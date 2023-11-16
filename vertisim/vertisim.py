import simpy
from typing import Any, Dict, List
from .sim_setup import SimSetup
from .aircraft.aircraft import AircraftStatus
from .utils.helpers import get_stopping_events, get_truncation_events
import time
import numpy as np
import gymnasium as gym
from .utils.get_state_variables import get_simulator_states
from .utils.fetch_data_from_db import fetch_latest_data_from_db
from .initiate_flow_entities import initiate_flow_entities
from .utils.units import sec_to_ms, ms_to_hr
from .run_step_by_step_simulation import run_step_by_step_simulation, run_steps_until_specific_events


class VertiSim:
    def __init__(self, 
                 env: simpy.Environment, 
                 config: Dict, 
                 reward_function_parameters: Dict = None):
        self.env = env
        self.config = config
        self.reward_function_parameters = reward_function_parameters
        self.terminal_event, self.truncation_event, self.truncation_events, self.stopping_events = self.set_simulation_events(env=self.env, config=self.config)

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
                                  truncation_events=self.truncation_events,
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
        truncation_events = get_truncation_events(env=env,
                                                  truncation_events=config["external_optimization_params"]["truncation_events"],
                                                  aircraft_count=self.get_aircraft_count())
        stopping_events = get_stopping_events(env=env, 
                                              stopping_events=config["external_optimization_params"]["stopping_events"],
                                              aircraft_count=self.get_aircraft_count(),
                                              vertiport_ids=self.get_vertiport_ids(),
                                              pax_count=self.get_passenger_count())
        return terminal_event, truncation_event, truncation_events, stopping_events

    def run(self):
        # This only runs uninterrupted simulation. No distinction for online optimization
        self.run_uninterrupted_simulation()          
        self.finalize_simulation()
        # performance_metrics = self.sim_setup.calculate_performance_metrics()
        # self.sim_setup.save_results(performance_metrics)

    def finalize_simulation(self):
        if not self.sim_setup.sim_mode['client_server']:
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
        if not self.terminal_event.triggered:
            return self.terminal_event.succeed()
    
    def step(self, actions):
        """
        Run the simulation for one timestep.
        """
        # Reset the rewards
        # self.reset_rewards()
        # # Get the number of triggers for this step
        total_triggers = sum(action != 0 for action in actions)
        # Apply the action
        self.env.process(self.apply_action(actions))
        # Advance to the next stopping event
        return self.advance_to_next_stopping_event(total_triggers)
       
    def apply_action(self, action: np.array):
        """
        Apply action to the simulation.

        Actions:
        0: Do nothing
        1: Idle to charge
        2: Idle to service (vertiport 1)
        """
        # print(f"Applying action: {action}")
        # print(f"Converted action: {action}")

        process_list = []
        for aircraft_id, aircraft in self.sim_setup.system_manager.aircraft_agents.items():
            if action[aircraft_id] == 0:
                aircraft.is_process_completed = True
            if action[aircraft_id] == 1:
                if aircraft.status == AircraftStatus.IDLE:
                    aircraft.status = AircraftStatus.CHARGE
                    aircraft.is_process_completed = False
            elif action[aircraft_id] == 2:
                if aircraft.status == AircraftStatus.IDLE:
                    aircraft.status = AircraftStatus.FLY  
                    aircraft.is_process_completed = False    
        for aircraft_id, aircraft in self.sim_setup.system_manager.aircraft_agents.items():
            if action[aircraft_id] == 1:
                process_list.append(self.env.process(aircraft.charge_aircraft(parking_space=aircraft.parking_space)))
            elif action[aircraft_id] == 2:
                process_list.append(self.env.process(self.sim_setup.system_manager.reserve_aircraft(aircraft)))
        yield self.env.all_of(process_list)

    def action_mask(self):
        """
        Create the action mask for the current state of the simulation.
        """
        mask = []
        for aircraft_id, aircraft in self.sim_setup.system_manager.aircraft_agents.items():
            if aircraft.status == AircraftStatus.IDLE \
                and aircraft.soc != 100 \
                    and aircraft.soc > self.config['aircraft_params']['min_reserve_soc']:
                mask.append([1, 1, 1])
            elif aircraft.status == AircraftStatus.IDLE \
                    and aircraft.soc <= self.config['aircraft_params']['min_reserve_soc']:
                mask.append([1, 1, 0])
            elif aircraft.status == AircraftStatus.IDLE and aircraft.soc >= 99:
                mask.append([1, 0, 1])
            elif aircraft.status == AircraftStatus.CHARGE:
                mask.append([1, 0, 0])
            elif aircraft.status == AircraftStatus.FLY:
                mask.append([1, 0, 0])
        # Flatten the mask
        return np.array(mask).flatten().tolist()

    def advance_to_next_stopping_event(self, total_triggers):
        """
        Runs the simulation until the next defined stopping event.
        """
        trigger_count = 0
        # Flag to check if any event was triggered
        stopping_event_triggered = False   
        # Flag to check if any truncation event was triggered
        truncation_triggered = False   
        
        stopped_events = set()
        truncated_events = set()

        while self._should_continue_simulation():
            # Print the next event
            # print(f"Next event: {self.env.peek()}")
            # Step the simulation
            self.env.step()

            # Check if any events in stopping_events have triggered.
            for event_name, event in self.stopping_events.items():
                if event.triggered and (event_name.startswith("passenger_arrival") and event_name not in stopped_events):
                    self._reset_event(event_name)
                if event.triggered and (not event_name.startswith("passenger_arrival") and event_name not in stopped_events):
                    trigger_count += 1
                     # Set the triggered flag to True
                    stopping_event_triggered = True 
                    # Add the event to the list of stopped events
                    stopped_events.add(event_name)

          
            # If there are any triggered stopping event, pop it out, reset it and return the states
            if len(self.sim_setup.system_manager.triggered_stopping_event_queue):
                event_name = self.sim_setup.system_manager.triggered_stopping_event_queue.pop()
                # print(f"Triggered event: {event_name}. Time sec: {round(self.env.now/1000)}. Reward: {self.calculate_reward()}. State: {self.get_current_state()['aircraft_states']}")
                # Reset the event
                self._reset_event(event_name)
                # Return the states
                # print(f"Aircraft status and location: {[(aircraft.status, aircraft.location) for _, aircraft in self.sim_setup.system_manager.aircraft_agents.items()]}")
                # print(f"Action mask: {self.action_mask()}")
                # print(f"REWARD: {self.calculate_reward()}")
                if trigger_count == total_triggers:
                    reward = round(self.calculate_reward())
                    self.reset_rewards()
                    # print(f"Reward: {reward}")
                else:
                    reward = 0
                # print(f"Reward: {reward}")
                return self.get_current_state(), reward, self.is_terminated(), self.is_truncated(), self.action_mask()


            # # # If any event was triggered and there is the list is cleared, return the states
            # if trigger_count == total_triggers and stopping_event_triggered:
            #     # Reset the triggered stopping events
            #     for event_name, event in self.stopping_events.items():
            #         if event.triggered:
            #             # Reset the event
            #             self._reset_event(event_name)                
            #     # Return the states
            #     reward = round(self.calculate_reward())
            #     self.reset_rewards()
            #     print(f"Reward: {reward}")
            #     return self.get_current_state(), reward, self.is_terminated(), self.is_truncated(), self.action_mask()

        # self._handle_end_of_simulation()
        self.finalize_simulation()
        # print(f"FINAL REWARD: {self.calculate_reward()}")
        # print(f"Simulation ended. Time sec: {round(self.env.now/1000)}. Reward: {self.calculate_reward()}. Returned state: {self.get_current_state()}")
        return self.get_current_state(), self.calculate_reward(), self.is_terminated(), self.is_truncated(), self.action_mask()

    def _should_continue_simulation(self):
        return (self.env.peek() < self.max_sim_time and 
                (not self.terminal_event.triggered and 
                not self.truncation_event.triggered and
                not self._check_demand_satisfied()))
    
    def _check_demand_satisfied(self):
        # If system_manager.passenger_arrival_complete == True and if there is no passenger left in the waiting rooms of the vertiports, succeed the terminal event
        # print(f"Total waiting passengers: {self.sim_setup.system_manager.get_total_waiting_passenger_count()} at time sec: {round(self.env.now/1000)}")
        if bool(
            self.sim_setup.system_manager.passenger_arrival_complete
            and self.sim_setup.system_manager.check_all_waiting_rooms_empty()
            and self.sim_setup.system_manager.is_all_passenger_travelled()):
            print("Demand satisfied")
            self.sim_setup.print_passenger_trip_time_stats()
            # self.sim_setup.system_manager.reward += \
            #     self.config['external_optimization_params']['reward_function_parameters']['completion_reward']
            self.terminal_event.succeed()
            return True
        return False
    
    def _reset_event(self, event_name):
        self.stopping_events[event_name] = self.env.event()

    def _handle_end_of_simulation(self):
        if self.env.peek() < self.max_sim_time and not self.terminal_event.triggered:
            self.terminal_event.succeed()

    def is_terminated(self):
        """
        Check if the simulation has terminated.
        """
        return self.terminal_event.triggered
    
    def is_truncated(self):
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
                    # Pop them out from the triggered event queue
                    self.sim_setup.system_manager.triggered_stopping_event_queue.pop()
        return self.get_current_state()
    
    
    def calculate_reward(self):
        """
        Calculate the reward for the current state of the simulation.
        """
        return sum(
            vertiport.get_exponential_waiting_cost()
            for _, vertiport in self.sim_setup.vertiports.items()) * \
                self.config['external_optimization_params']['reward_function_parameters']['waiting_time_penalty'] + \
                    self.sim_setup.system_manager.trip_counter * \
                        self.config['external_optimization_params']['reward_function_parameters']['trip_reward'] + \
            self.sim_setup.system_manager.trip_time_counter * \
                self.config['external_optimization_params']['reward_function_parameters']['flight_cost'] + \
            self.sim_setup.system_manager.truncation_penalty * \
                 self.config['external_optimization_params']['reward_function_parameters']['truncation_penalty'] + \
                self.sim_setup.system_manager.occupancy_reward + \
                self.sim_setup.system_manager.spill_counter * \
                self.config['external_optimization_params']['reward_function_parameters']['spill_cost'] +\
                self.sim_setup.system_manager.charge_reward * \
                self.config['external_optimization_params']['reward_function_parameters']['charge_reward']
    
    def reset_rewards(self):
        """
        Reset the rewards for the current state of the simulation.
        """
        self.sim_setup.system_manager.trip_counter = 0
        self.sim_setup.system_manager.trip_time_counter = 0
        self.sim_setup.system_manager.truncation_penalty = 0
        self.sim_setup.system_manager.occupancy_reward = 0
        self.sim_setup.system_manager.spill_counter = 0
        self.sim_setup.system_manager.charge_reward = 0

    @staticmethod
    def multidiscrete_to_discrete(action, n_actions=3):
        """Converts a MultiDiscrete action to a Discrete action."""
        discrete_action = 0
        for i, a in enumerate(reversed(action)):
            discrete_action += a * (n_actions ** i)
        return discrete_action

    @staticmethod
    def discrete_to_multidiscrete(action, dimensions=4, n_actions=3):
        """Converts a Discrete action back to a MultiDiscrete action."""
        multidiscrete_action = []
        for _ in range(dimensions):
            multidiscrete_action.append(action % n_actions)
            action = action // n_actions
        return list(reversed(multidiscrete_action))   
    

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
    
    def get_performance_metrics(self):
        return fetch_latest_data_from_db(db_path='sqlite/db/vertisimDatabase.sqlite')
