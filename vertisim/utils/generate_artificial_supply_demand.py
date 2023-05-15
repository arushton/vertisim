from typing import List
import numpy as np
import random
import pandas as pd
from utils.distribution_generator import DistributionGenerator
from utils.helpers import cumulative_sum_array, nested_dict_filter_keys
from utils.weighted_random_chooser import weighted_random_choose_exclude_element, random_choose_exclude_element
from typing import Dict

def generate_aircraft_network_schedule(vertiport_configs: Dict, 
                                       vertiport_layouts: Dict,
                                       aircraft_params: Dict,
                                       network_simulation: bool):
    """
    Generate artificial aircraft supply for each vertiport in the network.
    """
    network_schedule = pd.DataFrame(columns=['tail_number', 'aircraft_arrival_time', 'aircraft_departure_time', 
                                             'interarrival_time', 'origin_vertiport_id', 'destination_vertiport_id', 
                                             'passengers_onboard', 'location', 'soc'])
    for vertiport_id, vertiport_config in vertiport_configs.items():
        vertiport_schedule = generate_artificial_aircraft_supply(
            aircraft_arrival_process=vertiport_config['aircraft_arrival_process'],
            aircraft_params=aircraft_params,
            vertiport_id=vertiport_id,
            vertiport_layout=vertiport_layouts[vertiport_id],
            network_simulation=network_simulation
        )

        network_schedule = pd.concat([network_schedule, vertiport_schedule], ignore_index=True)

    # Sort the network_schedule by aircraft_arrival_time
    network_schedule.sort_values(by='aircraft_arrival_time', inplace=True)
    network_schedule.reset_index(drop=True, inplace=True)

    # Assign unique tail_numbers to all aircraft in the network
    network_schedule['tail_number'] = list(range(len(network_schedule)))

    return network_schedule


def generate_artificial_aircraft_supply(aircraft_arrival_process: Dict, 
                                        aircraft_params: Dict, 
                                        vertiport_id: str,
                                        vertiport_layout: object,
                                        network_simulation: bool):
    min_init_soc=aircraft_params['min_init_soc']
    max_init_soc=aircraft_params['max_init_soc']
    passenger_capacity=aircraft_params['pax']
    if not network_simulation:
        num_passengers = aircraft_arrival_process['num_passengers']
        num_aircraft = aircraft_arrival_process['num_aircraft']

        if num_passengers is None and num_aircraft is None:
            raise ValueError('Either num_passengers or num_aircraft must be defined.')
        if num_aircraft is None:
            num_aircraft = int(round(((num_passengers / passenger_capacity) + 1) * 2.5)) # 1/2.5 is the average aircraft load factor

        # Generate interarrival times. If constant interarrival time is defined, use that. Otherwise, use the distribution.
        # If neither is defined, raise an error.
        if aircraft_arrival_process['aircraft_interarrival_constant'] is None and aircraft_arrival_process['aircraft_arrival_distribution'] is None:
            raise ValueError('Either aircraft_interarrival_constant or aircraft_arrival_distribution must be defined.')
        if aircraft_arrival_process['aircraft_interarrival_constant'] is not None:
            interarrival_times = [aircraft_arrival_process['aircraft_interarrival_constant']] * num_aircraft
        else:
            distribution = DistributionGenerator(distribution_params=aircraft_arrival_process['aircraft_arrival_distribution'],
                                                max_val_in_dist=aircraft_arrival_process['aircraft_arrival_distribution']['max_val_in_dist'])
            interarrival_times = [distribution.pick_number_from_distribution() for _ in range(num_aircraft)]
        soc = [random.randint(min_init_soc, max_init_soc) for _ in range(num_aircraft)]
    else:
        # If network simulation, aircraft start from the ground with max_init_soc.
        num_aircraft = aircraft_arrival_process['num_initial_aircraft_in_vertiport']
        interarrival_times = [0 for _ in range(num_aircraft)]
        soc = [max_init_soc for _ in range(num_aircraft)]
        parking_pad_ids = vertiport_layout.parking_pad_ids
        location = [f'{parking_pad_ids.pop()}' for _ in range(num_aircraft)]


    aircraft_arrival_times = cumulative_sum_array(interarrival_times)
    aircraft_departure_times = [None for _ in range(num_aircraft)]
    origin_vertiport_id = [vertiport_id for _ in range(num_aircraft)]
    destination_vertiport_id = [vertiport_id for _ in range(num_aircraft)]
    passengers_onboard = [[] for _ in range(num_aircraft)]
    serviced_time_at_the_location = [0 for _ in range(num_aircraft)]
    priority = [1 for _ in range(num_aircraft)]
    speed = [0 for _ in range(num_aircraft)]


    return pd.DataFrame({'aircraft_arrival_time': aircraft_arrival_times,
                         'aircraft_departure_time': aircraft_departure_times,
                         'interarrival_time': interarrival_times,
                         'origin_vertiport_id': origin_vertiport_id,
                         'destination_vertiport_id': destination_vertiport_id,
                         'soc': soc,
                         'speed': speed,
                         'passengers_onboard': passengers_onboard,
                         'location': location,
                         'serviced_time_at_the_location': serviced_time_at_the_location,
                         'priority': priority
                         })


def generate_passenger_network_demand(vertiport_configs: Dict, 
                                      vertiport_ids: List,
                                      demand_probabilities: List,
                                      network_simulation: bool):
    """
    Generate artificial passenger demand for each vertiport in the network.
    """
    network_demand = pd.DataFrame()
    for vertiport_id, vertiport_config in vertiport_configs.items():
        vertiport_demand = generate_artificial_passenger_demand(
            passenger_arrival_process=vertiport_config['passenger_arrival_process'],
            vertiport_ids=vertiport_ids,
            origin_vertiport_id=vertiport_id,
            demand_probabilities=demand_probabilities,
            network_simulation=network_simulation
        )

        network_demand = pd.concat([network_demand, vertiport_demand], ignore_index=True)

    # Sort the network_demand by passenger_arrival_time
    network_demand.sort_values(by='passenger_arrival_time', inplace=True)
    network_demand.reset_index(drop=True, inplace=True)

    # Assign unique passenger_ids to all passengers in the network
    network_demand['passenger_id'] = list(range(len(network_demand)))

    return network_demand

def generate_artificial_passenger_demand(passenger_arrival_process: Dict,
                                         vertiport_ids: List,
                                         origin_vertiport_id: str,
                                         demand_probabilities: List,
                                         network_simulation: bool):
    num_passengers = passenger_arrival_process['num_passengers']
    if network_simulation and len(vertiport_ids) != len(demand_probabilities):
        raise ValueError('Number of vertiports and the length of demand_probabilities must be the same.')
    
    if network_simulation:
        dest_vertiport_ids = weighted_random_choose_exclude_element(elements_list=vertiport_ids, 
                                                                    exclude_element=origin_vertiport_id,
                                                                    probabilities=demand_probabilities, 
                                                                    num_selection=num_passengers)
    else:
        dest_vertiport_ids = random_choose_exclude_element(elements_list=vertiport_ids,
                                                           exclude_element=origin_vertiport_id,
                                                           num_selection=num_passengers)

    if passenger_arrival_process['passenger_arrival_distribution'] is None and passenger_arrival_process['passenger_interarrival_constant'] is None:
        raise ValueError('Either passenger_arrival_distribution or passenger_interarrival_constant must be defined.')
    if passenger_arrival_process['passenger_interarrival_constant'] is not None:
        interarrival_times = [passenger_arrival_process['passenger_interarrival_constant']] * num_passengers
    else:
        distribution = DistributionGenerator(distribution_params=passenger_arrival_process['passenger_arrival_distribution'])
        interarrival_times = [distribution.pick_number_from_distribution() for _ in range(num_passengers)]
    passenger_arrival_times = cumulative_sum_array(interarrival_times)

    return pd.DataFrame({'passenger_arrival_time': passenger_arrival_times,
                         'interarrival_time': interarrival_times,
                         'origin_vertiport_id': origin_vertiport_id,
                         'dest_vertiport_id': dest_vertiport_ids})