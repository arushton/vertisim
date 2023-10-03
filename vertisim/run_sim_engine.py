import simpy
from typing import Any, Dict, List
from utils.units import ms_to_min
from utils.helpers import get_passenger_id_str_from_passenger_list, careful_round, filter_nested_dict_by_given_keys
import numpy as np
from collections import defaultdict
from sim_setup import SimSetup

class RunSimEngine:
    def __init__(self, 
                 env: simpy.Environment, 
                 flight_schedule_file_path: str,
                 vertiports: Dict, 
                 airspace: object, 
                 structural_entity_groups: Dict,
                 system_manager: object,
                 max_sim_time: int,
                 simulation_states: List,
                 step_by_step_sim: bool = False,
                 response_type: str = 'auto',
                 terminal_event: object = None):
        self.env = env
        self.vertiports = vertiports
        self.airspace = airspace
        self.structural_entity_groups = structural_entity_groups
        self.system_manager = system_manager
        self.max_sim_time = max_sim_time
        self.simulation_states = simulation_states
        self.response_type = response_type
        self.terminal_event = terminal_event

        if not step_by_step_sim:
            self.run_uninterrupted_simulation(flight_schedule_file_path)
        else:
            while self.env.peek() < self.max_sim_time and self.terminal_event.triggered == False:
                self.env.step()
                # Check if any of the stopping events have occurred.
                for event_name, event in self.system_manager.stopping_event.items():
                    if event.triggered:
                        # Get the states
                        states = self.get_current_state()
                        # Reset the event
                        self.system_manager.stopping_event[event_name] = self.env.event()
                        

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
        """
        raise NotImplementedError
    
    def get_current_state(self):
        """
        Get the current state of the simulation.
        """
        return RunSimEngine.get_simulator_states(vertiports=self.vertiports,
                                        aircraft_agents=self.system_manager.aircraft_agents,
                                        num_aircraft=self.system_manager.num_aircraft,
                                        simulation_states=self.simulation_states)
    
    def get_initial_state(self):
        """
        Reset the simulation.
        """
        return RunSimEngine.get_initial_states()
    
    def calculate_reward(self):
        """
        Calculate the reward for the current state of the simulation.
        """
        raise NotImplementedError
    
    def advance_timestep(self):
        """
        Run the simulation until the next defined stopping event.
        """
        raise NotImplementedError
    
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

    @staticmethod
    def get_simulator_states(
        vertiports: Dict[str, Any],
        aircraft_agents: Dict[str, Any],
        num_aircraft: int,
        simulation_states: List[str]
    ) -> Dict[str, Any]:
        """
        Get the states for simulation entities.

        Args:
        - vertiports: Dictionary containing vertiport details.
        - aircraft_agents: Dictionary containing aircraft agent details.
        - num_aircraft: Total number of aircraft expected in simulation.
        - simulation_states: List of state keys to be filtered from the results.

        Returns:
        - Dictionary containing filtered states for vertiports, aircrafts, and environment.
        """

        # Return if not all aircraft are initialized.
        if len(aircraft_agents) < num_aircraft:
            return {}

        system_manager = RunSimEngine.get_system_manager(aircraft_agents)

        vertiport_states = {
            vertiport_id: RunSimEngine.filter_and_get_states(vertiport, vertiport.get_vertiport_states, simulation_states)
            for vertiport_id, vertiport in vertiports.items()
        }

        aircraft_states = {
            tail_number: RunSimEngine.filter_and_get_states(aircraft, aircraft.get_aircraft_states, simulation_states)
            for tail_number, aircraft in aircraft_agents.items()
        }

        environmental_states = system_manager.wind.get_wind_states()

        return {
            'vertiport_states': vertiport_states,
            'aircraft_states': aircraft_states,
            'environmental_states': environmental_states
        }

    @staticmethod
    def get_initial_states():
        raise NotImplementedError    
    
    @staticmethod
    def filter_and_get_states(entity, get_states_func, keys):
        """Helper function to get and filter states for given entity."""
        states = get_states_func(entity)
        return filter_nested_dict_by_given_keys(states, keys)

    @staticmethod
    def get_aircraft(aircraft_agents):
        return list(aircraft_agents.values())[0]

    @staticmethod
    def get_system_manager(aircraft_agents: Dict) -> object:
        return RunSimEngine.get_aircraft(aircraft_agents=aircraft_agents).system_manager    
