import simpy
from typing import Any, Dict, List
from utils.units import ms_to_min, sec_to_ms
from utils.get_state_variables import get_simulator_states
from utils.helpers import get_passenger_id_str_from_passenger_list, careful_round, filter_nested_dict_by_given_keys
import numpy as np
from collections import defaultdict

class SimEngineRunner:
    def __init__(self, 
                 env: simpy.Environment, 
                 sim_setup: object,
                 stopping_events: Dict = None,
                 reward_function_parameters: Dict = None,
                 terminal_event: object = None):
        self.env = env
        self.sim_setup = sim_setup
        self.stopping_events = stopping_events
        self.max_sim_time = sec_to_ms(self.sim_setup.sim_params['max_sim_time'])
        self.terminal_event = terminal_event
        self.reward_function_parameters = reward_function_parameters
                        
    def run_uninterrupted_simulation(self, flight_schedule_file_path):
        """
        Run the simulation until the max simulation time or there is no event left in the queue.
        """
        if flight_schedule_file_path is not None:
            self.env.run()
        else:
            self.env.run(until=self.max_sim_time)

    def apply_action(self, action: Any):
        """
        Apply action to the simulation.

        Actions:
        0: Do nothing
        1: Idle to charge
        2: Idle to service
        """
        pass
    
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
    
    def advance_to_next_stopping_event(self):
        """
        Run the simulation until the next defined stopping event.
        """
        while self.env.peek() < self.max_sim_time and self.terminal_event.triggered == False:
            self.env.step()
            # Check if any events in stopping_events have triggered.
            for event_name, event in self.stopping_events.items():
                if event.triggered:
                    # Get the states
                    states = self.get_current_state()
                    # Reset the event
                    self.stopping_events[event_name] = self.env.event()
                    # Return the states
                    return states, self.calculate_reward(), self.check_terminated() # TODO: Return check_truncated

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
        raise NotImplementedError 
