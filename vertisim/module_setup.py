from vertiport_layout_creator import VertiportLayout
from config import VertiportConfig, TaxiOperationsConfig
from vertiport_manager import VertiportManager


def create_vertiport_layout(file_path,
                            layout_type):
    return VertiportLayout(file_path,
                           layout_type)


def vertiport_config(env,
                     vertiport_layout,
                     vertiport_distances,
                     num_chargers,
                     shared_charger_sets,
                     num_security_check_servers):
    return VertiportConfig(env,
                           vertiport_layout,
                           vertiport_distances,
                           num_chargers,
                           shared_charger_sets,
                           num_security_check_servers)


def set_taxi_operations_config(is_simultaneous_taxi_and_take_off_allowed):
    TaxiOperationsConfig.is_simultaneous_taxi_and_take_off_allowed = is_simultaneous_taxi_and_take_off_allowed
    return TaxiOperationsConfig


def create_vertiport_manager(env,
                             vertiport,
                             scheduler,
                             arrival_priority,
                             departure_priority,
                             taxi_config,
                             aircraft_fleet_specs,
                             aircraft_energy_consumption_data,
                             charging_time_distribution_params,
                             passenger_distributions,
                             max_flight_waiting_time,
                             charging_interuption,
                             charger_efficiency,
                             charger_max_charge_rate,
                             min_reserve_soc,
                             event_saver):
    return VertiportManager(env,
                            vertiport,
                            scheduler,
                            arrival_priority,
                            departure_priority,
                            taxi_config,
                            aircraft_fleet_specs,
                            aircraft_energy_consumption_data,
                            charging_time_distribution_params,
                            passenger_distributions,
                            max_flight_waiting_time,
                            charging_interuption,
                            charger_efficiency,
                            charger_max_charge_rate,
                            min_reserve_soc,
                            event_saver)
