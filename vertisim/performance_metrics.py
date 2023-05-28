import numpy as np
import pandas as pd
from collections import defaultdict
from utils.units import ms_to_min, sec_to_min
from utils.helpers import nested_dict_all_values, remove_larger_keys, get_values_from_nested_dict, \
    get_length_of_longest_list, get_length_of_shortest_list
import matplotlib.pyplot as plt
from typing import List


class PerformanceMetrics:

    def __init__(self, 
                sim_start_timestamp, 
                aircraft_params,
                only_aircraft_simulation, 
                passenger_consolidation_time,
                passenger_departure_queue_count, 
                aircraft_arrival_queue_count, 
                aircraft_departure_queue_count,
                passenger_waiting_time, 
                passenger_transfer_time, 
                passenger_departure_queue_waiting_time,
                aircraft_holding_time,
                aircraft_charging_times,
                aircraft_taxi_times,
                flight_schedule,
                fato_usage_tracker, 
                aircraft_idle_time_tracker,
                sim_id, 
                verbose=False):
        self.sim_start_timestamp = sim_start_timestamp
        self.aircraft_params = aircraft_params
        self.only_aircraft_simulation = only_aircraft_simulation
        self.passenger_consolidation_time = passenger_consolidation_time
        self.passenger_departure_queue_count = passenger_departure_queue_count
        self.aircraft_arrival_queue_count = aircraft_arrival_queue_count
        self.aircraft_departure_queue_count = aircraft_departure_queue_count
        self.passenger_waiting_time = passenger_waiting_time
        self.passenger_transfer_time = passenger_transfer_time
        self.passenger_departure_queue_waiting_time = passenger_departure_queue_waiting_time
        self.aircraft_holding_time = aircraft_holding_time
        self.aircraft_charging_times=aircraft_charging_times,
        self.aircraft_taxi_times=aircraft_taxi_times,
        self.flight_schedule = flight_schedule
        self.fato_usage_tracker = fato_usage_tracker
        self.aircraft_idle_time_tracker = aircraft_idle_time_tracker
        self.sim_id = sim_id
        self.hour = 60 * 60 * 1000
        self.performance_metrics = defaultdict(dict)

        self.aircraft_arrival_queue_count = remove_larger_keys(self.aircraft_arrival_queue_count, self.flight_schedule)

        if not self.only_aircraft_simulation:
            self.calculate_passenger_consolidation_time_stats()
            self.calculate_passenger_waiting_time_stats()
            self.calculate_passenger_transfer_time_stats()
            self.calculate_passenger_departure_queue_count_stats()
            self.compute_total_passenger_throughput()
            self.compute_average_passenger_throughput()
            self.compute_load_factor_stats()
            self.compute_aircraft_idle_time_stats()
            self.calculate_passenger_departure_queue_waiting_times_stats()
        self.calculate_aircraft_arrival_queue_count_stats()
        self.calculate_aircraft_departure_queue_count_stats()
        self.compute_aircraft_throughput()
        self.compute_average_aircraft_throughput()
        self.compute_fato_utilization()
        self.calculate_aircraft_holding_times_stats()
        self.compute_average_charge_time()
        self.compute_average_taxi_time()
        self.compute_turnaround_duration()
        self.compute_tlof_reservation_duration()

        if verbose:
            self.print_verbose_performance_metrics()
        # else:
        #     self.print_performance_metrics()

    def calculate_passenger_consolidation_time_stats(self): # TODO: Fix this
        # Creates a dataframe for passenger consolidation time statistics including mean, median, standard deviation,
        # max and min
        consolidation_times = [x['consolidation_time'] for x in
                               list(nested_dict_all_values(self.passenger_consolidation_time, 1))]

        if consolidation_times:
            self.performance_metrics['passenger_consolidation_time']['mean'] = round(
                ms_to_min(np.mean(consolidation_times)), 2)
            self.performance_metrics['passenger_consolidation_time']['median'] = round(
                ms_to_min(np.median(consolidation_times)), 2)
            self.performance_metrics['passenger_consolidation_time']['std'] = round(ms_to_min(np.std(consolidation_times)),
                                                                                    2)
            self.performance_metrics['passenger_consolidation_time']['max'] = round(ms_to_min(np.max(consolidation_times)),
                                                                                    2)
            self.performance_metrics['passenger_consolidation_time']['min'] = round(ms_to_min(np.min(consolidation_times)),
                                                                                    2)
        else:
            # If all the passengers are flying on a different flight, then there is no consolidation time
            self.performance_metrics['passenger_consolidation_time']['mean'] = -1
            self.performance_metrics['passenger_consolidation_time']['median'] = -1
            self.performance_metrics['passenger_consolidation_time']['std'] = -1
            self.performance_metrics['passenger_consolidation_time']['max'] = -1
            self.performance_metrics['passenger_consolidation_time']['min'] = -1

    def calculate_passenger_waiting_time_stats(self):
        # Creates a dataframe for passenger waiting time statistics including mean, median, standard deviation,
        # waiting_times = [x['waiting_time'] for x in list(nested_dict_all_values(self.passenger_waiting_time, 1))]
        waiting_times = np.array(list(self.passenger_waiting_time.values()))

        self.performance_metrics['passenger_waiting_time']['mean'] = round(ms_to_min(np.mean(waiting_times)), 2)
        self.performance_metrics['passenger_waiting_time']['median'] = round(ms_to_min(np.median(waiting_times)), 2)
        self.performance_metrics['passenger_waiting_time']['std'] = round(ms_to_min(np.std(waiting_times)), 2)
        self.performance_metrics['passenger_waiting_time']['max'] = round(ms_to_min(np.max(waiting_times)), 2)
        self.performance_metrics['passenger_waiting_time']['min'] = round(ms_to_min(np.min(waiting_times)), 2)

    def calculate_passenger_transfer_time_stats(self):
        # Creates a dataframe for passenger transfer time statistics including mean, median, standard deviation,
        # max and min

        # transfer_times = [x['transfer_time'] for x in list(nested_dict_all_values(self.passenger_transfer_time, 1))]
        transfer_times = np.array(list(self.passenger_transfer_time.values()))

        self.performance_metrics['passenger_transfer_time']['mean'] = round(ms_to_min(np.mean(transfer_times)), 2)
        self.performance_metrics['passenger_transfer_time']['median'] = round(ms_to_min(np.median(transfer_times)), 2)
        self.performance_metrics['passenger_transfer_time']['std'] = round(ms_to_min(np.std(transfer_times)), 2)
        self.performance_metrics['passenger_transfer_time']['max'] = round(ms_to_min(np.max(transfer_times)), 2)
        self.performance_metrics['passenger_transfer_time']['min'] = round(ms_to_min(np.min(transfer_times)), 2)

    def calculate_passenger_departure_queue_count_stats(self):
        # Creates a dataframe for passenger departure queue count statistics including mean, median, standard deviation,
        self.performance_metrics['passenger_departure_queue_count']['mean'] = round(
            np.mean(list(self.passenger_departure_queue_count.values())), 2)
        self.performance_metrics['passenger_departure_queue_count']['median'] = round(
            np.median(list(self.passenger_departure_queue_count.values())), 2)
        self.performance_metrics['passenger_departure_queue_count']['std'] = round(
            np.std(list(self.passenger_departure_queue_count.values())), 2)
        self.performance_metrics['passenger_departure_queue_count']['max'] = max(list(self.passenger_departure_queue_count.values()))
        self.performance_metrics['passenger_departure_queue_count']['min'] = min(list(self.passenger_departure_queue_count.values()))

    def calculate_passenger_departure_queue_waiting_times_stats(self):
        # Creates a dataframe for passenger departure queue waiting times statistics including mean, median, standard deviation,
        # max and min
        
        waiting_times = np.array(list(self.passenger_departure_queue_waiting_time.values()))

        self.performance_metrics['passenger_departure_queue_waiting_times']['mean'] = round(ms_to_min(np.mean(waiting_times)), 2)
        self.performance_metrics['passenger_departure_queue_waiting_times']['median'] = round(ms_to_min(np.median(waiting_times)), 2)
        self.performance_metrics['passenger_departure_queue_waiting_times']['std'] = round(ms_to_min(np.std(waiting_times)), 2)
        self.performance_metrics['passenger_departure_queue_waiting_times']['max'] = round(ms_to_min(np.max(waiting_times)), 2)
        self.performance_metrics['passenger_departure_queue_waiting_times']['min'] = round(ms_to_min(np.min(waiting_times)), 2)

    def calculate_aircraft_arrival_queue_count_stats(self):
        # Creates a dataframe for aircraft arrival queue count statistics including mean, median, standard deviation,
        self.performance_metrics['aircraft_arrival_queue_count']['mean'] = round(
            np.mean(list(self.aircraft_arrival_queue_count.values())), 2)
        self.performance_metrics['aircraft_arrival_queue_count']['median'] = round(
            np.median(list(self.aircraft_arrival_queue_count.values())), 2)
        self.performance_metrics['aircraft_arrival_queue_count']['std'] = round(
            np.std(list(self.aircraft_arrival_queue_count.values())), 2)
        self.performance_metrics['aircraft_arrival_queue_count']['max'] = max(list(self.aircraft_arrival_queue_count.values()))
        self.performance_metrics['aircraft_arrival_queue_count']['min'] = min(list(self.aircraft_arrival_queue_count.values()))

    def calculate_aircraft_departure_queue_count_stats(self):
        # Creates a dataframe for aircraft departure queue count statistics including mean, median, standard deviation,
        self.performance_metrics['aircraft_departure_queue_count']['mean'] = round(
            np.mean(list(self.aircraft_departure_queue_count.values())), 2)
        self.performance_metrics['aircraft_departure_queue_count']['median'] = round(
            np.median(list(self.aircraft_departure_queue_count.values())), 2)
        self.performance_metrics['aircraft_departure_queue_count']['std'] = round(
            np.std(list(self.aircraft_departure_queue_count.values())), 2)
        self.performance_metrics['aircraft_departure_queue_count']['max'] = max(list(self.aircraft_departure_queue_count.values()))
        self.performance_metrics['aircraft_departure_queue_count']['min'] = min(list(self.aircraft_departure_queue_count.values()))

    def calculate_aircraft_holding_times_stats(self):
        # Creates a dataframe for aircraft arrival queue waiting times statistics including mean, median, standard deviation,
        # max and min
        
        waiting_times = np.array(list(self.aircraft_holding_time.values()))

        self.performance_metrics['aircraft_holding_times']['mean'] = round(ms_to_min(np.mean(waiting_times)), 2)
        self.performance_metrics['aircraft_holding_times']['median'] = round(ms_to_min(np.median(waiting_times)), 2)
        self.performance_metrics['aircraft_holding_times']['std'] = round(ms_to_min(np.std(waiting_times)), 2)
        self.performance_metrics['aircraft_holding_times']['max'] = round(ms_to_min(np.max(waiting_times)), 2)
        self.performance_metrics['aircraft_holding_times']['min'] = round(ms_to_min(np.min(waiting_times)), 2)

    def compute_load_factor_stats(self):
        # Computes load factor statistics
        flight_list = get_values_from_nested_dict(self.flight_schedule, 'passengers')
        self.performance_metrics['load_factor']['max'] = get_length_of_longest_list(flight_list)
        self.performance_metrics['load_factor']['min'] = get_length_of_shortest_list(flight_list)

        total_passengers = sum(len(flight) for flight in flight_list)
        avg_load_factor = total_passengers / len(flight_list)
        self.performance_metrics['load_factor']['mean'] = round(avg_load_factor, 2)

    def compute_aircraft_idle_time_stats(self):
        # Computes aircraft idle time statistics
        idle_times = list(self.aircraft_idle_time_tracker.values())
        self.performance_metrics['aircraft_idle_time']['max'] = round(ms_to_min(np.max(idle_times)), 2)
        self.performance_metrics['aircraft_idle_time']['min'] = round(ms_to_min(np.min(idle_times)), 2)
        self.performance_metrics['aircraft_idle_time']['mean'] = round(ms_to_min(np.mean(idle_times)), 2)
        self.performance_metrics['aircraft_idle_time']['median'] = round(ms_to_min(np.median(idle_times)), 2)
        self.performance_metrics['aircraft_idle_time']['std'] = round(ms_to_min(np.std(idle_times)), 2)

    def compute_average_charge_time(self):
        # Computes the average charge time
        total_charge_time = sum(self.aircraft_charging_times[0].values())
        total_aircraft = len(self.aircraft_charging_times[0].values())
        self.performance_metrics['average_charge_time'] = round(ms_to_min(total_charge_time / total_aircraft), 2)

    def compute_average_taxi_time(self):
        total_taxi_time = sum(self.aircraft_taxi_times[0].values())
        total_aircraft = len(self.aircraft_taxi_times[0].values())
        self.performance_metrics['average_taxi_time'] = round(ms_to_min(total_taxi_time / total_aircraft), 2)

    def compute_turnaround_duration(self):
        # Computes the average aircraft turnaround time
        turnaround_time = 2*self.performance_metrics['average_taxi_time'] + \
            self.performance_metrics['average_charge_time'] + \
            sec_to_min(self.aircraft_params['time_pre_charging_processes']) + \
            sec_to_min(self.aircraft_params['time_post_charging_processes']) + \
            sec_to_min(self.aircraft_params['time_charging_plug_disconnection'])
    
        self.performance_metrics['average_aircraft_turnaround_time'] = round(turnaround_time, 2)

    def compute_tlof_reservation_duration(self):
        tlof_time = self.aircraft_params['time_descend_transition'] + \
            self.aircraft_params['time_hover_descend'] + \
            self.aircraft_params['time_rotor_spin_down'] + \
            self.aircraft_params['time_post_landing_safety_checks'] + \
            self.aircraft_params['time_tug_connection'] + \
            self.aircraft_params['time_pre_take_off_check_list'] + \
            self.aircraft_params['time_rotor_spin_up'] + \
            self.aircraft_params['time_hover_climb'] + \
            self.aircraft_params['time_climb_transition'] + \
            self.performance_metrics['average_taxi_time']
        tlof_time = tlof_time / 2
        self.performance_metrics['tlof_time'] = round(ms_to_min(tlof_time), 2)

    def compute_total_passenger_throughput(self):
        # Computes the total passenger throughput
        total_passengers = sum(
            len(flight) for flight in get_values_from_nested_dict(self.flight_schedule, 'passengers'))
        self.performance_metrics['passenger_throughput']['total'] = total_passengers
        return total_passengers

    def compute_average_passenger_throughput(self):
        # Computes the passenger throughput skipping the first 1 hour of the simulation
        total_sim_time = self.calculate_total_simulated_time()
        first, second = self.get_time_interval(total_sim_time)
        interval_length = second - first
        total_passengers = sum(
            len(self.flight_schedule[key]['passengers'])
            for key, value in self.flight_schedule.items()
            if self.sim_start_timestamp + self.hour * first
            <= key
            <= self.sim_start_timestamp + second * self.hour
        )
        self.performance_metrics['passenger_throughput']['mean'] = total_passengers / interval_length
        return total_passengers / interval_length

    def get_time_interval(self, total_sim_time: int) -> List[int]:
        """
        Returns the time interval for the result indexing.
        :param total_sim_time: Total simulation time
        :return: Start of interval, end of interval
        """
        if total_sim_time < 4:
            raise ValueError(f'Simulation time is less than 4 hours ({total_sim_time} hrs). Simulation ID: {self.sim_id}')
        elif 4 < total_sim_time <= 5:
            return 2, 4
        elif 5 < total_sim_time <= 6:
            return 2, 5
        elif 6 < total_sim_time <= 7:
            return 2, 5
        elif 7 < total_sim_time <= 8:
            return 3, 6
        elif 8 < total_sim_time <= 9:
            return 3, 7
        elif 9 < total_sim_time <= 10:
            return 3, 8
        elif 10 < total_sim_time <= 11:
            return 4, 9
        elif 11 < total_sim_time <= 12:
            return 4, 9
        elif 12 < total_sim_time <= 15:
            return 4, 10
        elif 15 < total_sim_time <= 20:
            return 5, 13
        else:
            return 6, 15

    def compute_aircraft_throughput(self):
        # Computes the aircraft throughput
        self.performance_metrics['aircraft_throughput']['total'] = len(self.flight_schedule)
        return len(self.flight_schedule)

    def compute_average_aircraft_throughput(self):
        # Computes the passenger throughput
        total_sim_time = self.calculate_total_simulated_time()
        first, second = self.get_time_interval(total_sim_time)
        interval_length = second - first
        total_aircraft = 0
        for key, value in self.flight_schedule.items():
            if self.sim_start_timestamp + self.hour * first <= key <= self.sim_start_timestamp + second * self.hour:
                total_aircraft += 1
        self.performance_metrics['aircraft_throughput']['mean'] = total_aircraft / interval_length
        return total_aircraft

    def compute_aircraft_throughput_for_each_hour(self):
        # Computes the aircraft throughput for each hour
        total_sim_time = self.calculate_total_simulated_time()
        first, second = self.get_time_interval(total_sim_time)
        interval_length = second - first
        total_aircraft_at_each_hour = defaultdict(dict)
        for time_interval in range(first, second):
            total_aircraft_at_each_hour[time_interval] = 0
            for key, value in self.flight_schedule.items():
                if self.sim_start_timestamp + self.hour * time_interval <= key <= self.sim_start_timestamp + self.hour * (time_interval + 1):
                    total_aircraft_at_each_hour[time_interval] += 1
        return total_aircraft_at_each_hour

    def compute_fato_utilization(self):
        # Sums the difference between keys when the first value is 0 and the next value is 1.
        keys = list(self.fato_usage_tracker.keys())
        values = list(self.fato_usage_tracker.values())
        time_fato_empty = 0
        after_hour = []
        for i in range(len(keys) - 1):
            if keys[i] >= self.sim_start_timestamp + self.hour:
                after_hour.append(keys[i])
                if values[i] == 0 and values[i + 1] == 1:
                    time_fato_empty += keys[i + 1] - keys[i]

        total_sim_time = after_hour[-1] - after_hour[0]
        fato_utilization = round((total_sim_time - time_fato_empty) / total_sim_time * 100, 2)
        self.performance_metrics['fato_utilization'] = fato_utilization

    def print_passenger_consolidation_time_stats(self):
        print("Passenger consolidation time statistics in minutes:")
        print("-----------------------------")
        df = pd.DataFrame(
            {
                'mean': [self.performance_metrics['passenger_consolidation_time']['mean']],
                'median': [self.performance_metrics['passenger_consolidation_time']['median']],
                'std': [self.performance_metrics['passenger_consolidation_time']['std']],
                'max': [self.performance_metrics['passenger_consolidation_time']['max']],
                'min': [self.performance_metrics['passenger_consolidation_time']['min']]
            }
        )
        print(df)
        print("")

    def print_passenger_waiting_time_stats(self):
        print("Passenger waiting time statistics in minutes:")
        print("-----------------------------")
        df = pd.DataFrame(
            {
                'mean': [self.performance_metrics['passenger_waiting_time']['mean']],
                'median': [self.performance_metrics['passenger_waiting_time']['median']],
                'std': [self.performance_metrics['passenger_waiting_time']['std']],
                'max': [self.performance_metrics['passenger_waiting_time']['max']],
                'min': [self.performance_metrics['passenger_waiting_time']['min']]
            }
        )
        print(df)
        print("")

    def print_passenger_transfer_time_stats(self):
        print("Passenger transfer time statistics in minutes:")
        print("-----------------------------")
        df = pd.DataFrame(
            {
                'mean': [self.performance_metrics['passenger_transfer_time']['mean']],
                'median': [self.performance_metrics['passenger_transfer_time']['median']],
                'std': [self.performance_metrics['passenger_transfer_time']['std']],
                'max': [self.performance_metrics['passenger_transfer_time']['max']],
                'min': [self.performance_metrics['passenger_transfer_time']['min']]
            }
        )
        print(df)
        print("")

    def print_passenger_departure_queue_count_stats(self):
        print("Passenger departure queue count statistics:")
        print("-----------------------------")
        df = pd.DataFrame(
            {
                'mean': [self.performance_metrics['passenger_departure_queue_count']['mean']],
                'median': [self.performance_metrics['passenger_departure_queue_count']['median']],
                'std': [self.performance_metrics['passenger_departure_queue_count']['std']],
                'max': [self.performance_metrics['passenger_departure_queue_count']['max']],
                'min': [self.performance_metrics['passenger_departure_queue_count']['min']]
            }
        )
        print(df)
        print("")

    def print_aircraft_arrival_queue_count_stats(self):
        print("Aircraft arrival queue count statistics:")
        print("-----------------------------")
        df = pd.DataFrame(
            {
                'mean': [self.performance_metrics['aircraft_arrival_queue_count']['mean']],
                'median': [self.performance_metrics['aircraft_arrival_queue_count']['median']],
                'std': [self.performance_metrics['aircraft_arrival_queue_count']['std']],
                'max': [self.performance_metrics['aircraft_arrival_queue_count']['max']],
                'min': [self.performance_metrics['aircraft_arrival_queue_count']['min']]
            }
        )
        print(df)
        print("")

    def print_aircraft_holding_times_stats(self):
        print("Aircraft arrival queue waiting times statistics in minutes:")
        print("-----------------------------")
        df = pd.DataFrame(
            {
                'mean': [self.performance_metrics['aircraft_holding_times']['mean']],
                'median': [self.performance_metrics['aircraft_holding_times']['median']],
                'std': [self.performance_metrics['aircraft_holding_times']['std']],
                'max': [self.performance_metrics['aircraft_holding_times']['max']],
                'min': [self.performance_metrics['aircraft_holding_times']['min']]
            }
        )
        print(df)
        print("")

    def print_aircraft_departure_queue_count_stats(self):
        print("Aircraft departure queue count statistics:")
        print("-----------------------------")
        df = pd.DataFrame(
            {
                'mean': [self.performance_metrics['aircraft_departure_queue_count']['mean']],
                'median': [self.performance_metrics['aircraft_departure_queue_count']['median']],
                'std': [self.performance_metrics['aircraft_departure_queue_count']['std']],
                'max': [self.performance_metrics['aircraft_departure_queue_count']['max']],
                'min': [self.performance_metrics['aircraft_departure_queue_count']['min']]
            }
        )
        print(df)
        print("")

    def print_aircraft_idle_time_stats(self):
        print("Aircraft idle time statistics in minutes:")
        print("-----------------------------")
        df = pd.DataFrame(
            {
                'mean': [self.performance_metrics['aircraft_idle_time']['mean']],
                'median': [self.performance_metrics['aircraft_idle_time']['median']],
                'std': [self.performance_metrics['aircraft_idle_time']['std']],
                'max': [self.performance_metrics['aircraft_idle_time']['max']],
                'min': [self.performance_metrics['aircraft_idle_time']['min']]
            }
        )
        print(df)
        print("")

    def print_aircraft_throughput_stats_for_each_hr(self):
        print("Aircraft throughput statistics for each hour:")
        print("-----------------------------")
        total_aircraft_at_each_hour = self.compute_aircraft_throughput_for_each_hour()
        total_aircraft_at_each_hour = list(total_aircraft_at_each_hour.values())

    def print_aircraft_throughput_stats_for_each_hr_verbose(self):
        print("Aircraft throughput statistics for each hour:")
        print("-----------------------------")
        total_aircraft_at_each_hour = self.compute_aircraft_throughput_for_each_hour()
        total_aircraft_at_each_hour = list(total_aircraft_at_each_hour.values())
        print(f'Max number of departures during any 1-hr interval: {round(np.max(total_aircraft_at_each_hour), 2)}')
        print(f'Min number of departures during any 1-hr interval: {round(np.min(total_aircraft_at_each_hour), 2)}')
        print(f'Std of departures during 1 hr interval: {round(np.std(total_aircraft_at_each_hour), 2)}')

    def plot_aircraft_arrival_queue_count(self):
        # Plots aircraft arrival queue count
        plt.plot(
            np.round((np.array(list(self.aircraft_arrival_queue_count.keys())) - self.sim_start_timestamp) / 60000),
            list(self.aircraft_arrival_queue_count.values()),
            alpha=0.4)
        plt.xlabel('Time (min)')
        plt.ylabel('Aircraft Arrival Queue Count')
        plt.title('Aircraft Arrival Queue Count Over Time')
        plt.show()

    def calculate_total_simulated_time(self):
        # Calculates total simulated time
        total_simulated_time = round((list(self.flight_schedule.keys())[-1] - self.sim_start_timestamp)/self.hour, 2)
        self.performance_metrics['total_simulated_time'] = total_simulated_time
        return total_simulated_time

    def print_total_simulated_time(self):
        print(f"{self.calculate_total_simulated_time()} hours simulated")

    def print_avg_load_factor(self):
        print(f"Average load factor: {round(self.performance_metrics['load_factor']['mean'], 2)}")

    def print_total_aircraft_throughput(self):
        print(f"Total aircraft throughput: {round(self.performance_metrics['aircraft_throughput']['total'], 2)}")

    def print_average_aircraft_throughput(self):
        print(f"Average aircraft throughput in 1 hour: {round(self.performance_metrics['aircraft_throughput']['mean'], 2)}")

    def print_total_passenger_throughput(self):
        print(f"Total passenger throughput: {self.performance_metrics['passenger_throughput']['total']}")

    def print_average_passenger_throughput(self):
        print(f"Average passenger throughput in 1 hour: {self.performance_metrics['passenger_throughput']['mean']}")

    def print_fato_utilization(self):
        print(f"FATO utilization: {self.performance_metrics['fato_utilization']}%")

    def print_verbose_performance_metrics(self):
        if not self.only_aircraft_simulation:
            self.print_passenger_consolidation_time_stats()
            self.print_passenger_waiting_time_stats()
            self.print_passenger_transfer_time_stats()
            self.print_passenger_departure_queue_count_stats()
            self.print_avg_load_factor()
            self.print_aircraft_idle_time_stats()
            self.print_total_passenger_throughput()
            self.print_average_passenger_throughput()
        self.print_aircraft_arrival_queue_count_stats()
        self.print_aircraft_departure_queue_count_stats()
        self.print_aircraft_holding_times_stats()
        self.print_total_simulated_time()
        self.print_total_aircraft_throughput()
        self.print_aircraft_throughput_stats_for_each_hr_verbose()
        self.print_average_aircraft_throughput()
        self.print_fato_utilization()
        # self.plot_aircraft_arrival_queue_count()

    def print_performance_metrics(self):
        if not self.only_aircraft_simulation:
            self.print_avg_load_factor()
            self.print_total_passenger_throughput()
            self.print_average_passenger_throughput()
        self.print_total_simulated_time()
        self.print_total_aircraft_throughput()
        self.print_average_aircraft_throughput()
        self.print_aircraft_throughput_stats_for_each_hr()
        self.print_fato_utilization()
        # self.plot_aircraft_arrival_queue_count()
