import simpy
from typing import Any, Dict
from .sim_setup import SimSetup
from .utils.helpers import get_stopping_events
import time
import numpy as np
import gymnasium as gym
from .utils.get_state_variables import get_simulator_states
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
        self.terminal_event, self.truncation_event, self.stopping_events = VertiSim.set_simulation_events(env=self.env, config=self.config)

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
        self.max_sim_time = sec_to_ms(self.sim_setup.sim_params['max_sim_time'])

    @staticmethod
    def set_simulation_events(env, config):
        """
        Set the simulation events.
        """
        terminal_event = env.event()
        truncation_event = env.event()
        stopping_events = get_stopping_events(env=env, 
                                              stopping_events=config["external_optimization_params"]["stopping_events"])
        return terminal_event, truncation_event, stopping_events

    def print_total_time_to_run(self):
        end_time = time.time()
        time_taken = end_time - self.sim_start_time
        print(f'Simulation Completed. Total time to run: {round(time_taken, 2)} seconds')  

    def run(self):
        # This only runs uninterrupted simulation. No distinction for online optimization
        self.run_uninterrupted_simulation()
        self.finalize_simulation()

    def finalize_simulation(self):
        self.print_total_time_to_run()
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

    def run_client_server_simulation(self):
        pass

    def advance_to_next_stopping_event(self):
        """
        Runs the simulation until the next defined stopping event.
        """
        while self._should_continue_simulation():
            self.env.step()
            # Check if any events in stopping_events have triggered.
            for event_name, event in self.stopping_events.items():
                if event.triggered:
                    # Get the states
                    states = self.get_current_state()
                    # Reset the event
                    self._reset_event(event_name)
                    # Return the states
                    return states, self.calculate_reward(), self.check_terminated(), self.check_truncated()

        self._handle_end_of_simulation()
        self.finalize_simulation()
        return self.get_current_state(), self.calculate_reward(), self.check_terminated(), self.check_truncated()

    def _should_continue_simulation(self):
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

    def reset(self):
        """
        Reset the simulation.
        """
        return self.get_initial_state()
    
    def step(self, actions):
        """
        Run the simulation for one timestep.
        """
        # Apply the action
        self.env.process(self.apply_action(actions))
        # Advance to the next stopping event
        return self.advance_to_next_stopping_event()

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
        while self.sim_setup.system_manager.get_aircraft_count() < self.sim_setup.system_manager.num_initial_aircraft:
            self.env.step()
        return self.get_current_state()
    
    def calculate_reward(self):
        """
        Calculate the reward for the current state of the simulation.
        """
        return sum(
            vertiport.get_total_passenger_waiting_time()
            for _, vertiport in self.sim_setup.vertiports.items()
        )        

    def apply_action(self, action: np.array):
        """
        Apply action to the simulation.

        Actions:
        0: Do nothing
        1: Idle to charge
        2: Idle to service (vertiport 1)
        """
        process_list = []
        for aircraft_id, aircraft in self.sim_setup.system_manager.aircraft_agents.items():
            if action[aircraft_id] == 1:
                process_list.append(self.env.process(aircraft.charge_aircraft(parking_space=aircraft.parking_space)))
            elif action[aircraft_id] == 2:
                process_list.append(self.env.process(self.sim_setup.system_manager.reserve_aircraft(aircraft)))
        yield self.env.all_of(process_list)

    def set_action_space(self, config: Dict) -> gym.spaces.MultiDiscrete:
        """
        Creates the action space for each aircraft.
        """
        n_actions = self.get_action_count()
        n_aircraft = self.get_aircraft_count(config=config)
        return gym.spaces.MultiDiscrete([n_actions] * n_aircraft)
    
    def set_observation_space(self) -> gym.spaces.Box:
        # Vertiport states
        # Get the number of vertiports
        num_vertiports = len(self.config['network_and_demand_params']['vertiports'])

        # Get number of aircraft defined in the config file
        num_aircraft = self.get_aircraft_count()

        # Get the total number of state variables
        total_state_variables = num_vertiports * self.get_vertiport_state_variable_count() +\
                                num_aircraft * self.get_aircraft_state_variable_count() +\
                                num_vertiports * self.get_environmental_state_variable_count()
        
        # Return the observation space
        return gym.spaces.Box(low=0, high=np.inf, shape=(total_state_variables,), dtype=np.float32)
    
    def get_aircraft_count(self) -> int:
        return sum(
            vertiport['aircraft_arrival_process']['num_initial_aircraft_in_vertiport']
            for _, vertiport in self.config['network_and_demand_params']['vertiports'].items()
        )

    def get_vertiport_count(self) -> int:
        return len(self.sim_setup.vertiport_ids)
    
    def get_action_count(self):
        return self.config['external_optimization_params']['num_actions']

    def get_vertiport_state_variable_count(self):
        return self.config['external_optimization_params']['num_vertiport_state_variables']

    def get_aircraft_state_variable_count(self):
        return self.config['external_optimization_params']['num_aircraft_state_variables']
    
    def get_environmental_state_variable_count(self):
        return self.config['external_optimization_params']['num_environmental_state_variables']