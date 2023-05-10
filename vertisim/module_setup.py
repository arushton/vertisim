from vertiport_layout_creator import VertiportLayout
from config import VertiportConfig, TaxiOperationsConfig
from vertiport_manager import VertiportManager
from airspace_creator import AirspaceCreator
from airspace import Airspace
from collections import defaultdict
from typing import Dict, List


def create_vertiport_layouts(network_and_demand) -> None:
    layout_file_path = network_and_demand['vertiport_layout_file_path']
    vertiport_layouts = defaultdict(dict)
    for vertiport_id, vertiport_data in network_and_demand['vertiports'].items():
        layout = vertiport_data['layout']
        vertiport_layout = VertiportLayout(file_path=layout_file_path, 
                                           layout_type=layout,
                                           vertiport_id=vertiport_id)
        vertiport_layouts[vertiport_id] = vertiport_layout
    return vertiport_layouts

def create_airspace_layout(env: object, 
                            vertiports: Dict, 
                            vertiport_distances, 
                            airspace_params):
    if airspace_params['airspace_layout_file_path'] is not None:
        raise NotImplementedError("Airspace layout file path is not implemented yet. Use airspace creator.") # TODO: Implement airspace layout file path
    
    # Create the airspace layout
    airspace_creator = AirspaceCreator(vertiports=vertiports,
                                       airlink_segment_length_miles=airspace_params['airlink_segment_length'],
                                       vertiport_distances=vertiport_distances)
    return Airspace(env=env,
                    holding_unit_capacity=airspace_params['holding_unit_capacity'],
                    airlink_capacity=airspace_params['airlink_capacity'],
                    airlink_segment_length_miles=airspace_params['airlink_segment_length'],
                    waypoint_ids=airspace_creator.waypoint_ids,
                    waypoint_locations=airspace_creator.waypoint_locations)


def vertiport_config(env: object,
                     vertiports: dict,
                     vertiport_layouts: dict,
                     vertiport_ids: list) -> dict:
    
    return {vertiport_id: VertiportConfig(env=env,
                                          vertiport_id=vertiport_id,
                                          vertiport_data=vertiport_data,
                                          vertiport_layout=vertiport_layouts[vertiport_id],
                                          vertiport_ids=vertiport_ids)
                for vertiport_id, vertiport_data in vertiports.items()
            }

def set_taxi_operations_config(is_simultaneous_taxi_and_take_off_allowed) -> TaxiOperationsConfig:
    TaxiOperationsConfig.is_simultaneous_taxi_and_take_off_allowed = is_simultaneous_taxi_and_take_off_allowed
    return TaxiOperationsConfig


def create_vertiport_manager(env,
                             vertiports,
                             vertiport_ids,
                             scheduler,
                             arrival_priority,
                             departure_priority,
                             airspace,
                             taxi_config,
                             only_aircraft_simulation,
                             aircraft_params,
                             vertiport_distances,
                             aircraft_energy_consumption_data,
                             passenger_distributions,
                             max_flight_waiting_time,
                             charging_interuption,
                             event_saver,
                             network_simulation):
    return VertiportManager(env=env,
                            vertiports=vertiports,
                            vertiport_ids=vertiport_ids,
                            scheduler=scheduler,
                            arrival_priority=arrival_priority,
                            departure_priority=departure_priority,
                            airspace=airspace,
                            taxi_config=taxi_config,
                            only_aircraft_simulation=only_aircraft_simulation,
                            aircraft_params=aircraft_params,
                            vertiport_distances=vertiport_distances,
                            aircraft_energy_consumption_data=aircraft_energy_consumption_data,
                            passenger_distributions=passenger_distributions,
                            max_flight_waiting_time=max_flight_waiting_time,
                            charging_interuption=charging_interuption,
                            event_saver=event_saver,
                            network_simulation=network_simulation)
