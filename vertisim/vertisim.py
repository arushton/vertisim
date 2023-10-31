import simpy
from typing import Any, Dict
from .sim_setup import SimSetup
from .aircraft.aircraft import AircraftStatus
from .utils.helpers import get_stopping_events
import time
import numpy as np
import gymnasium as gym
from .utils.get_state_variables import get_simulator_states
from .initiate_flow_entities import initiate_flow_entities
from .utils.units import sec_to_ms
from .run_step_by_step_simulation import run_step_by_step_simulation, run_steps_until_specific_events


class VertiSim:
    def __init__(self, 
                 env: simpy.Environment, 
                 config: Dict, 
                 reward_function_parameters: Dict = None):
        self.env = env
        self.config = config
        self.reward_function_parameters = reward_function_parameters
        self.terminal_event, self.truncation_event, self.stopping_events = self.set_simulation_events(env=self.env, config=self.config)

        self.sim_start_time = time.time()
        self.sim_setup = SimSetup(env=self.env,
                                  sim_params=config['sim_params'],
                                  sim_mode=config['sim_mode'],
                                  external_optimization_params=config['external_optimization_params'],
                                  network_and_demand_params=config['network_and_demand_params'],
                                  airspace_params=config['airspace_params'],
                                  passenger_params=config['passenger_params'],
                                  aircraft_params=config['aircraft_params'],
                                  output_params=config['output_params'],
                                  stopping_events=self.stopping_events,
                                  truncation_event=self.truncation_event)    
        # Initiate flow entities and create events
        initiate_flow_entities(sim_setup=self.sim_setup)       
        # Set the max simulation time
        self.max_sim_time = sec_to_ms(self.sim_setup.sim_params['max_sim_time'])
        # The status of the simulation provides information whether the simulation running or not
        self.status = True
        # Remove the old logs.
        self.sim_setup.logger.remove_logs(seconds=10)


    def set_simulation_events(self, env, config):
        """
        Set the simulation events.
        """
        terminal_event = env.event()
        truncation_event = env.event()
        stopping_events = get_stopping_events(env=env, 
                                              stopping_events=config["external_optimization_params"]["stopping_events"],
                                              aircraft_count=self.get_aircraft_count(),
                                              vertiport_ids=self.get_vertiport_ids(),
                                              pax_count=self.get_passenger_count())
        return terminal_event, truncation_event, stopping_events

    def run(self):
        # This only runs uninterrupted simulation. No distinction for online optimization
        self.run_uninterrupted_simulation()          
        self.finalize_simulation()

    def finalize_simulation(self):
        self.print_total_time_to_run()
        if self.env.now > 0:
            performance_metrics = self.sim_setup.calculate_performance_metrics()
        self.sim_setup.save_results(performance_metrics)

    def run_uninterrupted_simulation(self):
        """
        Run the simulation until the max simulation time or there is no event left in the queue.
        """
        if self.sim_setup.sim_mode['offline_optimization']:
            self.env.run()
        else:
            self.env.run(until=self.max_sim_time)

    def reset(self):
        """
        Reset the simulation.
        """
        return self.terminal_event.succeed()
    
    def step(self, actions):
        """
        Run the simulation for one timestep.
        """
        # print(f"Running step. Current time: {self.env.now}")
        # Apply the action
        self.env.process(self.apply_action(actions))
        # Advance to the next stopping event
        return self.advance_to_next_stopping_event()

    def apply_action(self, action: np.array):
        """
        Apply action to the simulation.

        Actions:
        0: Do nothing
        1: Idle to charge
        2: Idle to service (vertiport 1)
        """
        print(f"Applying action: {action}")
        # action = VertiSim.discrete_to_multidiscrete(action, dimensions=self.get_aircraft_count(), base=3)
        # print(f"Converted action: {action}")

        process_list = []
        for aircraft_id, aircraft in self.sim_setup.system_manager.aircraft_agents.items():
            if action[aircraft_id] == 0 and aircraft.status == AircraftStatus.IDLE:
                self.sim_setup.system_manager.reward += 200
            elif action[aircraft_id] == 1:
                # print(f"Applying action to aircraft {aircraft_id}, type: {type(aircraft_id)}, action: {action[aircraft_id]}")
                process_list.append(self.env.process(aircraft.charge_aircraft(parking_space=aircraft.parking_space)))
            elif action[aircraft_id] == 2:
                process_list.append(self.env.process(self.sim_setup.system_manager.reserve_aircraft(aircraft)))
        yield self.env.all_of(process_list)
        # print("Finished applying action")

    @staticmethod
    def multidiscrete_to_discrete(action):
        """Converts a MultiDiscrete action to a Discrete action."""
        discrete_action = 0
        base = 3
        for i, a in enumerate(reversed(action)):
            discrete_action += a * (base ** i)
        return discrete_action

    @staticmethod
    def discrete_to_multidiscrete(action, dimensions=4, base=3):
        """Converts a Discrete action back to a MultiDiscrete action."""
        multidiscrete_action = []
        for _ in range(dimensions):
            multidiscrete_action.append(action % base)
            action = action // base
        return list(reversed(multidiscrete_action))        
    
    def advance_to_next_stopping_event(self):
        """
        Runs the simulation until the next defined stopping event.
        """
        # print(f"Active process: {self.env.active_process}, Time: {self.env.now}")
        while self._should_continue_simulation():
            # print(f"Next event scheduled at: {self.env.peek()}")
            self.env.step()
            # print(f"Stepping. Current time: {self.env.now}")
            triggered = False  # Flag to check if any event was triggered
            # Check if any events in stopping_events have triggered.
            for event_name, event in self.stopping_events.items():
                if event.triggered:  
                    # Reset the event
                    self._reset_event(event_name)  
                    # Set the triggered flag to True
                    triggered = True     
            if triggered:                  
                # Get the states
                states = self.get_current_state()
                # Return the states
                return states, self.calculate_reward(), self.check_terminated(), self.check_truncated()

        # self._handle_end_of_simulation()
        self.finalize_simulation()
        return self.get_current_state(), self.calculate_reward(), self.check_terminated(), self.check_truncated()

    def _should_continue_simulation(self):
        if self.terminal_event.triggered:
            print("Terminal event triggered")
        return (self.env.peek() < self.max_sim_time and 
                not self.terminal_event.triggered and 
                not self.truncation_event.triggered)
    
    def _reset_event(self, event_name):
        self.stopping_events[event_name] = self.env.event()

    def _handle_end_of_simulation(self):
        if self.env.peek() < self.max_sim_time:
            self.terminal_event.succeed()

    def check_terminated(self):
        """
        Check if the simulation has terminated.
        """
        return self.terminal_event.triggered
    
    def check_truncated(self):
        """
        Check if the simulation has truncated.
        """
        return self.truncation_event.triggered        

    def get_current_state(self):
        """
        Get the current state of the simulation.
        """
        return get_simulator_states(vertiports=self.sim_setup.vertiports,
                                    aircraft_agents=self.sim_setup.system_manager.aircraft_agents,
                                    num_initial_aircraft=self.sim_setup.system_manager.num_initial_aircraft,
                                    simulation_states=self.sim_setup.sim_params['simulation_states'])
    
    def get_initial_state(self):
        """
        Reset the simulation.
        """
        # print("Gettting the instance initial state")
        while self.sim_setup.system_manager.get_available_aircraft_count() < self.sim_setup.system_manager.num_initial_aircraft:          
            self.env.step()
            for event_name, event in self.stopping_events.items():
                if event.triggered:  
                    # Reset the event
                    self._reset_event(event_name) 
        return self.get_current_state()
    
    
    def calculate_reward(self):
        """
        Calculate the reward for the current state of the simulation.
        """
        return -10 * sum(
            vertiport.get_total_passenger_waiting_time()
            for _, vertiport in self.sim_setup.vertiports.items()
        )  + self.sim_setup.system_manager.trip_counter * 1000 - \
            self.sim_setup.system_manager.trip_time_counter * 10 + \
            self.sim_setup.system_manager.truncation_penalty + \
                self.sim_setup.system_manager.reward

    # def set_action_space(self, config: Dict) -> gym.spaces.Discrete:
    #     """
    #     Creates the action space for each aircraft.
    #     """
    #     n_actions = self.get_action_count()
    #     # n_aircraft = self.get_aircraft_count(config=config)
    #     # return gym.spaces.MultiDiscrete([n_actions] * n_aircraft)
    #     return gym.spaces.Discrete(n_actions)
    
    # def set_observation_space(self) -> gym.spaces.Box:
    #     # Vertiport states
    #     # Get the number of vertiports
    #     num_vertiports = len(self.config['network_and_demand_params']['vertiports'])

    #     # Get number of aircraft defined in the config file
    #     num_aircraft = self.get_aircraft_count()

    #     # Get the total number of state variables
    #     total_state_variables = num_vertiports * self.get_vertiport_state_variable_count() +\
    #                             num_aircraft * self.get_aircraft_state_variable_count() +\
    #                             num_vertiports * self.get_environmental_state_variable_count()
        
    #     # Return the observation space
    #     return gym.spaces.Box(low=0, high=np.inf, shape=(total_state_variables,), dtype=np.float32)
    
    def get_aircraft_count(self) -> int:
        return sum(
            vertiport['aircraft_arrival_process']['num_initial_aircraft_in_vertiport']
            for _, vertiport in self.config['network_and_demand_params']['vertiports'].items()
        )

    def get_vertiport_count(self) -> int:
        return len(self.sim_setup.vertiport_ids)
    
    def get_vertiport_ids(self) -> list:
        return list(self.config['network_and_demand_params']['vertiports'].keys())
    
    def get_action_count(self):
        return self.config['external_optimization_params']['num_actions']

    def get_vertiport_state_variable_count(self):
        return self.config['external_optimization_params']['num_vertiport_state_variables']

    def get_aircraft_state_variable_count(self):
        return self.config['external_optimization_params']['num_aircraft_state_variables']
    
    def get_environmental_state_variable_count(self):
        return self.config['external_optimization_params']['num_environmental_state_variables']
    
    def get_additional_state_variable_count(self):
        return self.config['external_optimization_params']['num_additional_state_variables']
    
    def get_passenger_count(self):
        return sum(
            vertiport['passenger_arrival_process']['num_passengers']
            for _, vertiport in self.config['network_and_demand_params']['vertiports'].items()
        )
    
    def print_total_time_to_run(self):
        end_time = time.time()
        time_taken = end_time - self.sim_start_time
        print(f'Simulation Completed. Total time to run: {round(time_taken, 2)} seconds')      
        