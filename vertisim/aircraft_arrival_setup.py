import pandas as pd

from aircraft import Aircraft
import numpy as np
import pandas as pd
from utils.units import sec_to_ms
from utils.helpers import compute_interarrival_times_from_schedule
from utils.generate_artificial_supply_demand import generate_aircraft_network_schedule
from typing import Dict, List, Union
# from scipy.stats import truncnorm
import scipy.stats as ss
from utils.read_files import read_input_file


class AircraftArrivalSetup:
    def __init__(self,
                 env: object,
                 network_simulation: bool,
                 vertiport_configs: Union[Dict, None],
                 aircraft_arrival_schedule_file_path: Union[str, None],
                 aircraft_params: Dict,
                 vertiport_manager: int,
                 event_saver: object):
        self.env = env
        self.network_simulation = network_simulation
        self.aircraft_arrival_schedule_file_path = aircraft_arrival_schedule_file_path
        self.vertiport_configs = vertiport_configs
        self.aircraft_params = aircraft_params
        self.vertiport_manager = vertiport_manager
        self.event_saver = event_saver
        self.num_aircraft = None

    def check_aircraft_arrival_schedule(self, aircraft_arrival_schedule: pd.DataFrame):
        """
        Check if the columns of the input file are correct.
        :param aircraft_arrival_schedule:
        :return:
        """
        # Check if aircraft arrival time exists in the input file.
        if 'aircraft_arrival_time' not in aircraft_arrival_schedule.columns:
            raise ValueError('aircraft_arrival_time column is not exist in the aircraft arrival process file.')
        
        # Check if aircraft departure time exists in the input file.
        if 'aircraft_departure_time' not in aircraft_arrival_schedule.columns:
            raise ValueError('aircraft_departure_time column is not exist in the aircraft arrival process file.')

        # Check if tail number exists in the input file.
        if 'tail_number' not in aircraft_arrival_schedule.columns:
            raise ValueError('tail_number column is not exist in the aircraft arrival process file.')

        # Check if vertiport_id column exists in the input file.
        if 'vertiport_id' not in aircraft_arrival_schedule.columns:
            raise ValueError('vertiport_id column is not exist in the aircraft arrival process file.')

        # Check if aircraft type exists in the input file.
        if 'aircraft_model' not in aircraft_arrival_schedule.columns:
            aircraft_arrival_schedule['aircraft_model'] = self.aircraft_params['aircraft_model']
        print(
            f"Aircraft model is not defined in the input file. The default aircraft type of {self.aircraft_params['aircraft_model']} is used. If you want to "
            "define the each aircraft type, please add the column 'aircraft_model' to the input file.")

        # Check if range of aircraft exists in the input file.
        if 'range' not in aircraft_arrival_schedule.columns:
            aircraft_arrival_schedule['range'] = self.aircraft_params['range']
        print(
            f"Aircraft range is not defined in the input file. The default aircraft range of {self.aircraft_params['range']} is used. If you want to "
            "define the range for each aircraft model, please add the column 'range' to the input file.")

        # Check if passenger capacity exists in the input file.
        if 'passenger_capacity' not in aircraft_arrival_schedule.columns:
            aircraft_arrival_schedule['passenger_capacity'] = self.aircraft_params['passenger_capacity']
        print(
            f"Passenger capacity is not defined in the input file. The default passenger capacity of {self.aircraft_params['passenger_capacity']} is used. If you "
            "want to define the passenger capacity for each aircraft type, please add the column "
            "'passenger_capacity' to the input file.")

        # Check if initial state of charge exists in the input file.
        if 'initial_soc' not in aircraft_arrival_schedule.columns:
            aircraft_arrival_schedule['initial_soc'] = self.aircraft_params['max_init_soc']
        print(
            f"Initial state of charge is not defined in the input file. The default initial state of charge of {self.aircraft_params['initial_soc']} is used. If you "
            "want to define the initial state of charge for each aircraft type, please add the column "
            "'max_init_soc' to the input file.")

        # Check if interarrival column time exists in the input file.
        if 'interarrival_time' not in aircraft_arrival_schedule.columns:
            aircraft_arrival_schedule['interarrival_time'] = compute_interarrival_times_from_schedule(
                aircraft_arrival_schedule['aircraft_arrival_time'])

    def setup_aircraft_arrival(self):
        if self.aircraft_arrival_schedule_file_path is not None:
            # Load aircraft arrival schedule from the path provided on self.aircraft_arrival_schedule.
            aircraft_arrival_schedule = read_input_file(self.aircraft_arrival_schedule_file_path)
            # Check if the columns of the input file are correct.
            self.check_aircraft_arrival_schedule(aircraft_arrival_schedule)
            print("Success: Aircraft arrival schedule loaded from file.")
        else:
            # Generate artificial aircraft arrival schedule.
            aircraft_arrival_schedule = generate_aircraft_network_schedule(
                vertiport_configs=self.vertiport_configs,
                aircraft_params=self.aircraft_params,
                network_simulation=self.network_simulation)
        # Get the number of aircraft.
        self.num_aircraft = len(aircraft_arrival_schedule)
        return aircraft_arrival_schedule

    def create_aircraft_arrival(self):
        # Create aircraft arrival process.
        aircraft_arrival_schedule = self.setup_aircraft_arrival()
        # Tail numbers start from 0 and ends at the number of aircraft-1.

        for tail_number in aircraft_arrival_schedule.tail_number:
            # Get the arrival time of the aircraft.
            interarrival_time = aircraft_arrival_schedule.loc[aircraft_arrival_schedule.tail_number == tail_number,
                                                              'interarrival_time'].values[0]
            # Get the initial state of charge of the aircraft.
            initial_soc = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'initial_soc'].values[0]
            # Get the aircraft type of the aircraft.
            aircraft_model = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'aircraft_model'].values[0]
            
            # Get the passenger capacity of the aircraft.
            passenger_capacity = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'passenger_capacity'].values[0]
            
            # Get the maximum range of the aircraft.
            max_range = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'max_range'].values[0]
            
            # Get the arrival vertiport id of the aircraft.
            arrival_vertiport_id = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'vertiport_id'].values[0]

            yield self.env.timeout(sec_to_ms(interarrival_time))

            # TODO: Agent should be created anywhere in the simulation. vertiport_id key should be changed to location_id.
            self.event_saver.save_agent_creation_time(agent_id=tail_number,
                                                      vertiport_id=arrival_vertiport_id,
                                                      agent_type='aircraft',
                                                      aircraft_model=aircraft_model)
                    
            # Simulate the aircraft.
            self.initiate_aircraft_arrival(tail_number=tail_number,
                                           initial_soc=initial_soc,
                                           aircraft_model=aircraft_model,
                                           max_range=max_range,
                                           passenger_capacity=passenger_capacity,
                                           arrival_vertiport_id=arrival_vertiport_id)

    def initiate_aircraft_arrival(self, tail_number: int,
                                  initial_soc: int,
                                  aircraft_model: str,
                                  passenger_capacity: int,
                                  max_range: int,
                                  arrival_vertiport_id: str):
        aircraft = Aircraft(env=self.env,
                            tail_number=tail_number,
                            arrival_vertiport_id=arrival_vertiport_id,
                            initial_soc=initial_soc,
                            arrival_time=self.env.now,
                            aircraft_params=self.aircraft_params,
                            passenger_capacity=passenger_capacity,
                            max_range=max_range,
                            aircraft_model=aircraft_model,
                            vertiport_manager=self.vertiport_manager,
                            event_saver=self.event_saver
                            )

        self.env.process(self.vertiport_manager.simulate_aircraft_arrival_process(aircraft))

    # def check_aircraft_arrival_input(self):
    #     if self.aircraft_arrival_schedule_file_path is not None and self.artificial_aircraft_arrival_process is not None:
    #         raise ValueError('Aircraft arrival schedule and aircraft arrival distribution cannot be defined at the '
    #                          'same time. Please only provide one of them.')

    # def get_aircraft_arrival_distribution(self):
    #     interarrival_time_population, interarrival_time_probabilities = generate_distribution(
    #         distribution_params=self.artificial_aircraft_arrival_process,
    #         max_val_in_dist=self.max_charge_duration)
    #     print('Aircraft arrival distribution is created.')
    #     return interarrival_time_population, interarrival_time_probabilities

    # def aircraft_arrival_interval_with_params(self):
    #     random_interval = np.random.normal(loc=self.time_aircraft_arrival_interval_parameters['mean'],
    #                                        scale=self.time_aircraft_arrival_interval_parameters['std'],
    #                                        size=1)[0]
    #
    #     return round(sec_to_ms(random_interval))

    # def aircraft_arrival_interval_with_params(self):
    #     truncated_normal_distribution = get_truncated_normal(mean=time_aircraft_arrival_interval_parameters['mean'],
    #                                                          std=time_aircraft_arrival_interval_parameters['std'],
    #                                                          low=round(time_aircraft_arrival_interval_parameters['mean']-time_aircraft_arrival_interval_parameters['std']/2),
    #                                                          upp=time_aircraft_arrival_interval_parameters['std']*4)
    #     random_arrival_interval = truncated_normal_distribution.rvs()

    # def aircraft_arrival_interval_with_params(self):
    #     random_arrival_interval = trunc_exp_rv(low=self.time_aircraft_arrival_interval_parameters['low'],
    #                                            high=self.time_aircraft_arrival_interval_parameters['high'],
    #                                            scale=self.time_aircraft_arrival_interval_parameters['scale'],
    #                                            size=1
    #                                            )[0]
    #
    #     return round(sec_to_ms(random_arrival_interval))

    # def trunc_exp_rv(low=30, high=300, scale=30, size=1):
    #     rnd_cdf = np.random.uniform(ss.expon.cdf(x=low, scale=scale),
    #                                 ss.expon.cdf(x=high, scale=scale),
    #                                 size=size)
    #     return ss.expon.ppf(q=rnd_cdf, scale=scale)
