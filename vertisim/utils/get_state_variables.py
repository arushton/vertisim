from typing import Dict
from collections import defaultdict
import json
import subprocess
from utils.units import ms_to_min
from utils.helpers import get_passenger_id_str_from_passenger_list, careful_round
import numpy as np

"""
Human readable state variables are the exhaustive list of state variables that are used for humman-in-the-loop simulation.
They are requndant for any external applications (AI and Optimization algorithms) that use the simulation as the environment.

Machine readable state variables are the minimal set of state variables that are useful for external applications.
If needed, modify the following function to return the minimal set of state variables that are useful for your application:
collect_structural_entity_state_variables_machine_readable(.)
collect_flow_entity_state_variables_machine_readable(.)
"""

def get_human_readable_state_variables(vertiports:Dict, airspace_states: Dict, aircraft_agents: Dict, passenger_agents: Dict):
    structural_entity_states = collect_structural_entity_state_variables_human_readable(vertiports, airspace_states)

    flow_entity_states = collect_flow_entity_state_variables_human_readable(aircraft_agents=aircraft_agents, passenger_agents=passenger_agents)
    if len(flow_entity_states) == 0:
        flow_entity_states = {'Flow Entities': None}
    # Merge the two dictionaries
    flow_entity_states |= structural_entity_states

    # # Convert the state variables to JSON and write to a file
    with open('../../output/state.json', 'w') as f:
        json.dump(flow_entity_states, f, default=str, indent=4)    

    # Open the JSON file in an editor
    subprocess.run(['open', '../../output/state.json'])  


def collect_structural_entity_state_variables_human_readable(vertiports: Dict, airspace_states: Dict):
    states = defaultdict(lambda: defaultdict(dict))
    for _, vertiport in vertiports.items():
        states |= vertiport.get_vertiport_states_dict()
    states |= airspace_states
    return {'Structural Entities': states}


def collect_flow_entity_state_variables_human_readable(aircraft_agents: Dict, passenger_agents: Dict):
    aircraft_states = defaultdict(dict)
    for tail_number, aircraft in aircraft_agents.items():
        aircraft_states[tail_number] = {
            'state': aircraft.detailed_status,
            'location': aircraft.location,
            'serviced_time_at_the_location': aircraft.serviced_time_at_the_location,
            'horizontal_speed': aircraft.forward_velocity,
            'vertical_velocity': aircraft.vertical_velocity,
            'altitude': aircraft.altitude,            
            'flight_direction': aircraft.flight_direction,
            'soc': aircraft.soc,
            'passengers_onboard': get_passenger_id_str_from_passenger_list(aircraft.passengers_onboard),
            'vertiport_arrival_time': careful_round(ms_to_min(aircraft.arrival_time), 2),
            'vertiport_departure_time': careful_round(ms_to_min(aircraft.departure_time), 2),
            'holding_time': careful_round(ms_to_min(aircraft.holding_time), 2),
            'flight_duration': careful_round(ms_to_min(aircraft.flight_duration), 2),
            'turnaround_time': careful_round(ms_to_min(aircraft.turnaround_time), 2),
            'priority': aircraft.priority,
            'parking_space_id': aircraft.parking_space_id,
            'fato_id': aircraft.assigned_fato_id
            # 'process': aircraft.process
        }

    passenger_states = defaultdict(dict)
    for passenger_id, passenger in passenger_agents.items():
        passenger_states[passenger_id] = {
            'location': passenger.location,
            'origin_vertiport_id': passenger.origin_vertiport_id,
            'destination_vertiport_id': passenger.destination_vertiport_id,
            'vertiport_arrival_time': careful_round(ms_to_min(passenger.vertiport_arrival_time), 2),
            'vertiport_departure_time': careful_round(ms_to_min(passenger.departure_time), 2)
        }
        
    aircraft_states |= passenger_states
    return aircraft_states


def get_simulator_states(vertiports: Dict, aircraft_agents: Dict, passenger_agents: Dict, num_aircraft: int):
    # Return if the number of aircraft is less than the number of aircraft specified in the simulation parameters.
    # We want all the states after all the aircraft have been initialized.
    if len(aircraft_agents) < num_aircraft:
        return
        
    system_manager = get_system_manager(aircraft_agents)

def get_machine_readable_state_variables(vertiports: Dict, airspace_states: np.array, aircraft_agents: Dict, num_aircraft: int):

    # Return if the number of aircraft is less than the number of aircraft specified in the simulation parameters.
    # We want all the states after all the aircraft have been initialized.
    if len(aircraft_agents) < num_aircraft:
        return
    
    structural_entity_states = collect_structural_entity_state_variables_machine_readable(vertiports, airspace_states)

    flow_entity_states = collect_flow_entity_state_variables_machine_readable(aircraft_agents=aircraft_agents)

    # TODO: Temporary solution. DO NOT HARDCODE THE NUMBER OF AIRCRAFT STATES
    if len(flow_entity_states) < num_aircraft*5:
        # Return if all aircraft have not been initialized
        return
    # Merge the arrays
    states = np.concatenate((structural_entity_states, flow_entity_states))

    if len(states) == 0:
        print('No states to save')

    # Save numpy array to a file
    np.save('../../output/state.npy', states)


def collect_structural_entity_state_variables_machine_readable(vertiports: Dict, airspace_states: np.array):
    states = np.array([])
    for _, vertiport in vertiports.items():
        states = np.concatenate((states, vertiport.get_vertiport_states_array()))
    states = np.concatenate((states, airspace_states))
    return states


def collect_flow_entity_state_variables_machine_readable(aircraft_agents: Dict):
    aircraft_states = np.array([])
    node_locations_list = get_node_location_list(aircraft_agents)
    vertiport_list = get_vertiport_list(aircraft_agents)

    for tail_number, aircraft in aircraft_agents.items():
        states = np.array([
            node_locations_list.index(aircraft.location),
            vertiport_list.index(aircraft.destination_vertiport_id),
            round(aircraft.soc),
            len(aircraft.passengers_onboard),
            # TODO: Add Estimated Remaining Trip Time
            aircraft.status.value
        ])
        aircraft_states = np.concatenate((aircraft_states, states))

    return aircraft_states

def get_aircraft(aircraft_agents):
    return list(aircraft_agents.values())[0]

def get_node_location_list(aircraft_agents):
    return list(get_system_manager(aircraft_agents=aircraft_agents).node_locations.keys())

def get_vertiport_list(aircraft_agents):
    return get_system_manager(aircraft_agents=aircraft_agents).vertiport_ids

def get_system_manager(aircraft_agents: Dict) -> object:
    return get_aircraft(aircraft_agents=aircraft_agents).system_manager