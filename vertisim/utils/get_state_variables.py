from typing import Dict
from collections import defaultdict
import json
import subprocess
from utils.units import ms_to_min
from utils.helpers import get_passenger_id_str_from_passenger_list, careful_round


def collect_structural_entity_state_variables(vertiports: Dict, airspace_states: Dict):
    states = defaultdict(lambda: defaultdict(dict))
    for _, vertiport in vertiports.items():
        states |= vertiport.vertiport_resource_states
    states |= airspace_states
    return {'Structural Entities': states}

def collect_flow_entity_state_variables(aircraft_agents: Dict, passenger_agents: Dict):
    aircraft_states = defaultdict(dict)
    for tail_number, aircraft in aircraft_agents.items():
        aircraft_states[tail_number] = {
            'flight_phase': aircraft.flight_phase,
            'location': aircraft.location,
            'serviced_time_at_the_location': aircraft.serviced_time_at_the_location,
            'horizontal_speed': aircraft.speed,
            'vertical_velocity': aircraft.vertical_velocity,
            'altitude': aircraft.altitude,            
            'flight_direction': aircraft.flight_direction,
            'soc': aircraft.soc,
            'passengers_onboard': get_passenger_id_str_from_passenger_list(aircraft.passengers_onboard),
            'vertiport_arrival_time': careful_round(ms_to_min(aircraft.arrival_time), 2),
            'vertiport_departure_time': careful_round(ms_to_min(aircraft.departure_time), 2),
            'holding_time': careful_round(ms_to_min(aircraft.holding_time), 2),
            'flight_time': careful_round(ms_to_min(aircraft.flight_time), 2),
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

def get_state_variables(vertiports:Dict, airspace_states: Dict, aircraft_agents: Dict, passenger_agents: Dict):
    structural_entity_states = collect_structural_entity_state_variables(vertiports, airspace_states)

    flow_entity_states = collect_flow_entity_state_variables(aircraft_agents=aircraft_agents, passenger_agents=passenger_agents)
    if len(flow_entity_states) == 0:
        flow_entity_states = {'Flow Entities': None}
    # Merge the two dictionaries
    flow_entity_states |= structural_entity_states

    # # Convert the state variables to JSON and write to a file
    with open('../../output/state.json', 'w') as f:
        json.dump(flow_entity_states, f, default=str, indent=4)    

    # Open the JSON file in an editor
    subprocess.run(['open', '../../output/state.json'])  
