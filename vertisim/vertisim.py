import simpy
from typing import Any, Dict, List
from .sim_setup import SimSetup
from .aircraft.aircraft import AircraftStatus
from .utils.helpers import get_stopping_events, get_truncation_events, miliseconds_to_hms, \
    create_action_enum, convert_action_values_to_enum, create_action_dict, reverse_dict, current_and_lookahead_pax_count
import time
import numpy as np
import gymnasium as gym
from collections import defaultdict
import pprint
from enum import Enum
from .utils.get_state_variables import get_simulator_states
from .utils import rl_utils
from .rl_methods.reward_function import RewardFunction
from .rl_methods.action_mask import ActionMask
from .utils.fetch_data_from_db import fetch_latest_data_from_db
from .initiate_flow_entities import initiate_flow_entities
from .utils.units import sec_to_ms, ms_to_hr, sec_to_min
from .run_step_by_step_simulation import run_step_by_step_simulation, run_steps_until_specific_events


class VertiSim:
    def __init__(self, 
                 env: simpy.Environment, 
                 config: Dict):
        self.env = env
        self.config = config
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
        # initiate_flow_entities(sim_setup=self.sim_setup)       
        # Set the max simulation time
        self.max_sim_time = sec_to_ms(self.sim_setup.sim_params['max_sim_time'])
        # The status of the simulation provides information whether the simulation running or not
        # Remove the old logs.
        # self.sim_setup.logger.remove_logs(seconds=10)

        if self.config['sim_mode']['rl']:
            self.setup_for_rl()

        self.status = True

    def setup_for_rl(self):
        # self.actions = create_action_enum(self.sim_setup.vertiport_ids)        
        self.action_dict = create_action_dict(self.sim_setup.vertiport_ids)
        self.reverse_action_dict = reverse_dict(self.action_dict)
        self.reward_function = RewardFunction(config=self.config, reverse_action_dict=self.reverse_action_dict, sim_setup=self.sim_setup)

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
        # self.sim_setup.print_passenger_trip_time_stats()

    def finalize_simulation(self):
        if not self.sim_setup.sim_mode['rl']:
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
        # Get the number of triggers for this step
        total_triggers = sum(action != 0 for action in actions)
        # Apply the actions and rewards at the same time to keep the Markov property
        self.env.process(self.apply_action_reward(actions=actions))
        # Advance to the next stopping event. The returned state and rewward pair should be
        # the state and reward after all the actions are applied.
        return self.advance_to_next_stopping_event_setting(total_triggers)

    def apply_action_reward(self, actions: Enum):
        """
        Apply action to the simulation and compute the reward before execution.
        We change the state of the aircrafts based on the action before we step the simulation
        to be able to calculate the reward at the same time for the given action list.

        Actions:
        0, 1, ..., N-1: Idle to fly to vertiport n
        N: Idle to charge
        N+1: Do nothing
        """
        # print(f"Applying action: {actions}")

        process_list = []
        for aircraft_id, aircraft in self.sim_setup.system_manager.aircraft_agents.items():
            # Charge the aircraft
            if actions[aircraft_id] == self.reverse_action_dict['CHARGE']:
                aircraft.status = AircraftStatus.CHARGE
                aircraft.is_process_completed = False
            # Do nothing
            elif actions[aircraft_id] == self.reverse_action_dict['DO_NOTHING']:
                aircraft.is_process_completed = True
            # Fly to the vertiport
            elif actions[aircraft_id] < self.sim_setup.num_vertiports():
                aircraft.status = AircraftStatus.FLY  
                aircraft.is_process_completed = False
                aircraft.current_vertiport_id = aircraft.get_aircraft_vertiport()
                aircraft.origin_vertiport_id = aircraft.current_vertiport_id
                aircraft.destination_vertiport_id = self.sim_setup.vertiport_index_to_id_map[actions[aircraft_id]]
            else:
                raise ValueError(f"Invalid action: {actions[aircraft_id]}")
                
        # Compute the reward
        self.reward_function.compute_reward(actions=actions)

        # Apply the actions
        for aircraft_id, aircraft in self.sim_setup.system_manager.aircraft_agents.items():
            if actions[aircraft_id] == self.reverse_action_dict['CHARGE']:
                process_list.append(self.env.process(aircraft.charge_aircraft(parking_space=aircraft.parking_space)))
            elif actions[aircraft_id] < self.sim_setup.num_vertiports():
                destination_vertiport_id = self.sim_setup.vertiport_index_to_id_map[actions[aircraft_id]]
                process_list.append(self.env.process(self.sim_setup.system_manager.reserve_aircraft(aircraft=aircraft, 
                                                                                                    destination_vertiport_id=destination_vertiport_id)))
        yield self.env.all_of(process_list)    

    def action_mask(self):
        """
        Create the action mask for the current state of the simulation.
        [Fly, Charge, Do nothing]
        """
        mask = []
        for aircraft_id, aircraft in self.sim_setup.system_manager.aircraft_agents.items():
            # Can do any action
            if aircraft.status == AircraftStatus.IDLE \
                and aircraft.soc <= 100-self.config['external_optimization_params']['soc_increment_per_charge_event'] \
                    and aircraft.soc >= self.config['aircraft_params']['min_reserve_soc']:
                destination_mask = [1 if destination != aircraft.current_vertiport_id 
                                    else 0 for destination in self.sim_setup.vertiport_ids]
                mask.extend(destination_mask + [1, 1])
            # Can only charge
            elif aircraft.status == AircraftStatus.IDLE \
                    and aircraft.soc <= self.config['aircraft_params']['min_reserve_soc']:
                destination_mask = [0] * self.sim_setup.num_vertiports()
                mask.extend(destination_mask + [1, 0])
            # Can fly and do nothing
            elif aircraft.status == AircraftStatus.IDLE and aircraft.soc > 100-self.config['external_optimization_params']['soc_increment_per_charge_event']:
                destination_mask = [1 if destination != aircraft.current_vertiport_id 
                                    else 0 for destination in self.sim_setup.vertiport_ids] 
                mask.extend(destination_mask + [0, 1])               
            elif aircraft.status == AircraftStatus.CHARGE or aircraft.status == AircraftStatus.FLY:
                destination_mask = [0] * self.sim_setup.num_vertiports()
                mask.extend(destination_mask + [0, 1])               
            
        # Review the mask based on demand. If there is no current and future demand at any particular vertiport, mask out the action
        for vertiport_id, vertiport in self.sim_setup.vertiports.items():
            if current_and_lookahead_pax_count(vertiport) == 0:
                # Find the index of the vertiport in the mask for each aircraft and mask out the action
                vertiport_index = self.sim_setup.vertiport_id_to_index_map[vertiport_id]
                # Iterate through each aircraft's part of the mask
                for i in range(0, len(mask), self.sim_setup.num_vertiports() + 2):
                    mask[i + vertiport_index] = 0                        
                    
        # Flatten the mask
        return np.array(mask).flatten().tolist()          

    def advance_to_next_stopping_event_setting(self, total_triggers):
        """
        Runs the simulation until the next defined stopping event.
        Rewards the agent right after the each action is completed.
        Rewards the agent separately for each action.
        """

        while self._should_continue_simulation():
            # Step the simulation
            self.env.step()
          
            # If there are any triggered stopping event queue, pop it out, reset it and return the states
            if len(self.sim_setup.system_manager.triggered_stopping_event_queue):
                # Pop the event on top of the queue
                event_name = self.sim_setup.system_manager.triggered_stopping_event_queue.pop()
                # print(f"Triggered event: {event_name}")
                # Reset the event
                self._reset_event(event_name)
                # Return the states
                reward = round(self.reward_function.reward, 2)
                self.reward_function.reset_rewards()
                # print(f"Reward: {reward}")
                # pprint.pprint(f"Currrent state: {self.get_current_state()}")
                return self.get_current_state(), reward, self.is_terminated(), self.is_truncated(), self.action_mask()

        self.finalize_simulation()
        return self.get_current_state(), round(self.reward_function.reward, 2), self.is_terminated(), self.is_truncated(), self.action_mask()    

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
            # print("Demand satisfied")
            # self.sim_setup.print_brief_metrics()
            # self.sim_setup.system_manager.reward += \
            #     self.config['external_optimization_params']['reward_function_parameters']['completion_reward']
            self.terminal_event.succeed()
            return True
        return False
    
    def _reset_event(self, event_name):
        """
        Reset the event by creating a new event.
        """
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
                                    simulation_states=self.sim_setup.sim_params['simulation_states'],
                                    reward_function_parameters=self.config['external_optimization_params']['reward_function_parameters'])
    
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
    
    def get_num_waiting_passengers_per_destination(self, vertiport_id):
        """
        Check the number of waiting passengers at the given vertiport.
        """
        return self.sim_setup.vertiports[vertiport_id].get_waiting_passenger_count()

    def print_total_time_to_run(self):
        end_time = time.time()
        time_taken = end_time - self.sim_start_time
        print(f'Simulation Completed. Total time to run: {round(time_taken, 2)} seconds')   
    
    def get_performance_metrics(self):
        return fetch_latest_data_from_db(db_path="sqlite/db/vertisimDatabase.sqlite")