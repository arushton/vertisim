from typing import Dict
from collections import defaultdict
import json
import subprocess
from utils.helpers import get_passenger_id_str_from_passenger_list


def collect_structural_entity_state_variables(vertiports: Dict, airspace_states: Dict):
    states = defaultdict(lambda: defaultdict(dict))
    for _, vertiport in vertiports.items():
        states |= vertiport.vertiport_resource_states
    states |= airspace_states
    return {'Structural Entities': states}

def collect_flow_entity_state_variables(aircraft_agents: Dict):
    states = defaultdict(dict)
    for tail_number, aircraft in aircraft_agents.items():
        states[tail_number] = {
            'soc': aircraft.soc,
            'location': aircraft.location,
            'serviced_time_at_the_location': aircraft.serviced_time_at_the_location,
            'flight_direction': aircraft.flight_direction,
            'passengers_onboard': get_passenger_id_str_from_passenger_list(aircraft.passengers_onboard),
            'vertiport_arrival_time': aircraft.arrival_time,
            'vertiport_departure_time': aircraft.departure_time,
            'priority': aircraft.priority,
            'parking_space_id': aircraft.parking_space_id,
            'fato_id': aircraft.assigned_fato_id,
            'speed': aircraft.speed
        }
    return states

def get_state_variables(vertiports:Dict, airspace_states: Dict, aircraft_agents: Dict):
    structural_entity_states = collect_structural_entity_state_variables(vertiports, airspace_states)

    flow_entity_states = collect_flow_entity_state_variables(aircraft_agents)
    if len(flow_entity_states) == 0:
        flow_entity_states = {'Flow Entities': None}
    # Merge the two dictionaries
    flow_entity_states |= structural_entity_states

    # # Convert the state variables to JSON and write to a file
    with open('state.json', 'w') as f:
        json.dump(flow_entity_states, f, default=str, indent=4)    

    # Open the JSON file in an editor
    subprocess.run(['open', 'state.json'])  
