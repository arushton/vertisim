from typing import List
import numpy as np
import random
import pandas as pd
from utils.distribution_generator import DistributionGenerator
from utils.helpers import cumulative_sum_array, nested_dict_filter_keys
from typing import Dict


def generate_artificial_aircraft_aircraft_supply(aircraft_fleet_specs: Dict, aircraft_arrival_process: Dict):
    num_passengers = aircraft_arrival_process['num_passengers']
    num_aircraft = aircraft_arrival_process['num_aircraft']
    avg_aircraft_capacity = np.mean(list(nested_dict_filter_keys(aircraft_fleet_specs, 2, 'pax')))

    if num_passengers is None and num_aircraft is None:
        raise ValueError('Either num_passengers or num_aircraft must be defined.')
    if num_aircraft is None:
        num_aircraft = int(round(((num_passengers / avg_aircraft_capacity) + 1) * 2.5))
    tail_numbers = list(range(num_aircraft))

    distribution = DistributionGenerator(distribution_params=aircraft_arrival_process,
                                         max_val_in_dist=aircraft_arrival_process['max_interarrival_time'])
    interarrival_times = [distribution.pick_number_from_distribution() for _ in range(num_aircraft)]
    aircraft_arrival_times = cumulative_sum_array(interarrival_times)
    initial_soc = [random.randint(aircraft_arrival_process['min_init_soc'],
                                  aircraft_arrival_process['max_init_soc']
                                  ) for _ in range(num_aircraft)]
    aircraft_model_list = [random.choice(list(aircraft_fleet_specs.keys())) for _ in range(num_aircraft)]

    return pd.DataFrame({'tail_number': tail_numbers,
                         'aircraft_arrival_time': aircraft_arrival_times,
                         'interarrival_time': interarrival_times,
                         'initial_soc': initial_soc,
                         'aircraft_model': aircraft_model_list})


def generate_artificial_passenger_demand(passenger_arrival_process: Dict,
                                         flight_destination_ids: List):
    num_passengers = passenger_arrival_process['passenger_arrival_distribution']['num_passengers']
    max_interarrival_time = passenger_arrival_process['passenger_arrival_distribution']['max_val_in_dist']

    passenger_ids = list(range(num_passengers))
    distribution = DistributionGenerator(distribution_params=passenger_arrival_process['passenger_arrival_distribution'],
                                         max_val_in_dist=max_interarrival_time)
    interarrival_times = [distribution.pick_number_from_distribution() for _ in range(num_passengers)]
    passenger_arrival_times = cumulative_sum_array(interarrival_times)
    dest_vertiport_ids = [random.choice(flight_destination_ids) for _ in range(num_passengers)]

    return pd.DataFrame({'passenger_id': passenger_ids,
                         'passenger_arrival_time': passenger_arrival_times,
                         'interarrival_time': interarrival_times,
                         'dest_vertiport_id': dest_vertiport_ids}).astype(np.int32)
