from vertiport_layout_creator import VertiportLayout
from config import VertiportConfig, TaxiOperationsConfig
from vertiport_manager import VertiportManager


def create_vertiport_layouts(network_and_demand) -> None:
    layout_file_path = network_and_demand['vertiport_layout_file_path']
    for vertiport_id, vertiport_data in network_and_demand['vertiports'].items():
        layout = vertiport_data['layout']
        vertiport_layout = VertiportLayout(file_path=layout_file_path, 
                                           layout_type=layout,
                                           vertiport_id=vertiport_id)
        vertiport_data['vertiport_layout'] = vertiport_layout


def vertiport_config(env: object,
                     vertiports: dict,
                     vertiport_ids: list) -> dict:
    
    return {vertiport_id: VertiportConfig(env,
                                            vertiport_id,
                                            vertiport_data,
                                            vertiport_ids)
                for vertiport_id, vertiport_data in vertiports.items()
            }

def set_taxi_operations_config(is_simultaneous_taxi_and_take_off_allowed) -> TaxiOperationsConfig:
    TaxiOperationsConfig.is_simultaneous_taxi_and_take_off_allowed = is_simultaneous_taxi_and_take_off_allowed
    return TaxiOperationsConfig


def create_vertiport_manager(env,
                             vertiports,
                             scheduler,
                             arrival_priority,
                             departure_priority,
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
    return VertiportManager(env,
                            vertiports,
                            scheduler,
                            arrival_priority,
                            departure_priority,
                            taxi_config,
                            only_aircraft_simulation,
                            aircraft_params,
                            vertiport_distances,
                            aircraft_energy_consumption_data,
                            passenger_distributions,
                            max_flight_waiting_time,
                            charging_interuption,
                            event_saver,
                            network_simulation)
