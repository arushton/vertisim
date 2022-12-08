import numpy as np
import pandas as pd
from collections import defaultdict
from utils.units import ms_to_min
from utils.helpers import nested_dict_all_values, remove_larger_keys, get_values_from_nested_dict, \
    get_length_of_longest_list, get_length_of_shortest_list
import matplotlib.pyplot as plt


class PerformanceMetrics:

    def __init__(self, sim_start_timestamp, passenger_consolidation_time, passenger_departure_queue_count,
                 aircraft_arrival_queue_count,
                 aircraft_departure_queue_count, passenger_waiting_time, passenger_transfer_time, flight_schedule,
                 fato_usage_tracker, verbose=False):
        self.sim_start_timestamp = sim_start_timestamp
        self.passenger_consolidation_time = passenger_consolidation_time
        self.passenger_departure_queue_count = passenger_departure_queue_count
        self.aircraft_arrival_queue_count = aircraft_arrival_queue_count
        self.aircraft_departure_queue_count = aircraft_departure_queue_count
        self.passenger_waiting_time = passenger_waiting_time
        self.passenger_transfer_time = passenger_transfer_time
        self.flight_schedule = flight_schedule
        self.fato_usage_tracker = fato_usage_tracker
        self.hour = 60 * 60 * 1000
        self.performance_metrics = defaultdict(dict)

        self.aircraft_arrival_queue_count = remove_larger_keys(self.aircraft_arrival_queue_count, self.flight_schedule)

        self.compute_load_factor_stats()
        self.compute_aircraft_throughput()

        self.calculate_passenger_consolidation_time_stats()
        self.calculate_passenger_waiting_time_stats()
        self.calculate_passenger_transfer_time_stats()
        self.calculate_passenger_departure_queue_count_stats()
        self.calculate_aircraft_arrival_queue_count_stats()
        self.calculate_aircraft_departure_queue_count_stats()
        self.compute_load_factor_stats()
        self.compute_total_passenger_throughput()
        self.compute_average_passenger_throughput()
        self.compute_aircraft_throughput()
        self.compute_average_aircraft_throughput()
        self.compute_fato_utilization()

        if verbose:
            self.print_performance_metrics()

    def calculate_passenger_consolidation_time_stats(self):
        # Creates a dataframe for passenger consolidation time statistics including mean, median, standard deviation,
        # max and min
        consolidation_times = [x['consolidation_time'] for x in
                               list(nested_dict_all_values(self.passenger_consolidation_time, 1))]

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

    def calculate_passenger_waiting_time_stats(self):
        # Creates a dataframe for passenger waiting time statistics including mean, median, standard deviation,
        waiting_times = [x['waiting_time'] for x in list(nested_dict_all_values(self.passenger_waiting_time, 1))]

        self.performance_metrics['passenger_waiting_time']['mean'] = round(ms_to_min(np.mean(waiting_times)), 2)
        self.performance_metrics['passenger_waiting_time']['median'] = round(ms_to_min(np.median(waiting_times)), 2)
        self.performance_metrics['passenger_waiting_time']['std'] = round(ms_to_min(np.std(waiting_times)), 2)
        self.performance_metrics['passenger_waiting_time']['max'] = round(ms_to_min(np.max(waiting_times)), 2)
        self.performance_metrics['passenger_waiting_time']['min'] = round(ms_to_min(np.min(waiting_times)), 2)

    def calculate_passenger_transfer_time_stats(self):
        # Creates a dataframe for passenger transfer time statistics including mean, median, standard deviation,
        # max and min

        transfer_times = [x['transfer_time'] for x in list(nested_dict_all_values(self.passenger_transfer_time, 1))]

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
        self.performance_metrics['passenger_departure_queue_count']['max'] = round(
            np.max(list(self.passenger_departure_queue_count.values())), 2)
        self.performance_metrics['passenger_departure_queue_count']['min'] = round(
            np.min(list(self.passenger_departure_queue_count.values())), 2)

    def calculate_aircraft_arrival_queue_count_stats(self):
        # Creates a dataframe for aircraft arrival queue count statistics including mean, median, standard deviation,
        self.performance_metrics['aircraft_arrival_queue_count']['mean'] = round(
            np.mean(list(self.aircraft_arrival_queue_count.values())), 2)
        self.performance_metrics['aircraft_arrival_queue_count']['median'] = round(
            np.median(list(self.aircraft_arrival_queue_count.values())), 2)
        self.performance_metrics['aircraft_arrival_queue_count']['std'] = round(
            np.std(list(self.aircraft_arrival_queue_count.values())), 2)
        self.performance_metrics['aircraft_arrival_queue_count']['max'] = round(
            np.max(list(self.aircraft_arrival_queue_count.values())), 2)
        self.performance_metrics['aircraft_arrival_queue_count']['min'] = round(
            np.min(list(self.aircraft_arrival_queue_count.values())), 2)

    def calculate_aircraft_departure_queue_count_stats(self):
        # Creates a dataframe for aircraft departure queue count statistics including mean, median, standard deviation,
        self.performance_metrics['aircraft_departure_queue_count']['mean'] = round(
            np.mean(list(self.aircraft_departure_queue_count.values())), 2)
        self.performance_metrics['aircraft_departure_queue_count']['median'] = round(
            np.median(list(self.aircraft_departure_queue_count.values())), 2)
        self.performance_metrics['aircraft_departure_queue_count']['std'] = round(
            np.std(list(self.aircraft_departure_queue_count.values())), 2)
        self.performance_metrics['aircraft_departure_queue_count']['max'] = round(
            np.max(list(self.aircraft_departure_queue_count.values())), 2)
        self.performance_metrics['aircraft_departure_queue_count']['min'] = round(
            np.min(list(self.aircraft_departure_queue_count.values())), 2)

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

    def compute_load_factor_stats(self):
        # Computes load factor statistics
        flight_list = get_values_from_nested_dict(self.flight_schedule, 'passengers')
        self.performance_metrics['load_factor']['max'] = get_length_of_longest_list(flight_list)
        self.performance_metrics['load_factor']['min'] = get_length_of_shortest_list(flight_list)

        total_passengers = sum(len(flight) for flight in flight_list)
        avg_load_factor = total_passengers / len(flight_list)
        self.performance_metrics['load_factor']['mean'] = round(avg_load_factor, 2)

    def compute_total_passenger_throughput(self):
        # Computes the total passenger throughput
        total_passengers = sum(
            len(flight) for flight in get_values_from_nested_dict(self.flight_schedule, 'passengers')) / 2
        self.performance_metrics['passenger_throughput']['total'] = total_passengers
        return total_passengers

    def compute_average_passenger_throughput(self):
        # Computes the passenger throughput skipping the first 1 hour of the simulation
        total_passengers = 0
        for key, value in self.flight_schedule.items():
            if self.sim_start_timestamp + self.hour <= key <= self.sim_start_timestamp + 2 * self.hour:
                total_passengers += len(self.flight_schedule[key]['passengers'])

        self.performance_metrics['passenger_throughput']['mean'] = total_passengers / 2
        return total_passengers / 2

    def compute_aircraft_throughput(self):
        # Computes the aircraft throughput
        self.performance_metrics['aircraft_throughput']['total'] = len(self.flight_schedule) / 2
        return len(self.flight_schedule) / 2

    def compute_average_aircraft_throughput(self):
        # Computes the passenger throughput
        total_aircraft = 0
        for key, value in self.flight_schedule.items():
            if self.sim_start_timestamp + self.hour <= key <= self.sim_start_timestamp + 2 * self.hour:
                if self.flight_schedule[key]['event'] == 'take_off':
                    total_aircraft += 1
        self.performance_metrics['aircraft_throughput']['mean'] = total_aircraft
        return total_aircraft

    def compute_fato_utilization(self):
        # Sums the difference between keys when the first value is 0 and the next value is 1.
        keys = list(self.fato_usage_tracker.keys())
        values = list(self.fato_usage_tracker.values())
        time_fato_empty = 0
        for i in range(2, len(keys) - 1):
            if values[i] == 0:
                if values[i + 1] == 1:
                    time_fato_empty += keys[i + 1] - keys[i]

        total_sim_time = keys[-1] - keys[2]
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
        print(self.calculate_aircraft_arrival_queue_count_stats())
        print("")

    def print_aircraft_departure_queue_count_stats(self):
        print("Aircraft departure queue count statistics:")
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

    def print_total_simulated_time(self):
        total_simulated_time = round((list(self.flight_schedule.keys())[-1] - self.sim_start_timestamp)/self.hour, 2)
        print(f"{total_simulated_time} hours simulated")

    def print_avg_load_factor(self):
        print(f"Average load factor: {self.performance_metrics['load_factor']['mean']}")

    def print_total_aircraft_throughput(self):
        print(f"Total aircraft throughput: {self.performance_metrics['aircraft_throughput']['total']}")

    def print_average_aircarft_throughput(self):
        print(f"Average aircraft throughput in 1 hour: {self.performance_metrics['aircraft_throughput']['mean']}")

    def print_total_passenger_throughput(self):
        print(f"Total passenger throughput: {self.performance_metrics['passenger_throughput']['total']}")

    def print_average_passenger_throughput(self):
        print(f"Average passenger throughput in 1 hour: {self.performance_metrics['passenger_throughput']['mean']}")

    def print_fato_utilization(self):
        print(f"FATO utilization: {self.performance_metrics['fato_utilization']}%")

    def print_performance_metrics(self):
        self.print_passenger_consolidation_time_stats()
        self.print_passenger_waiting_time_stats()
        self.print_passenger_transfer_time_stats()
        self.print_passenger_departure_queue_count_stats()
        self.print_aircraft_arrival_queue_count_stats()
        self.print_aircraft_departure_queue_count_stats()
        self.print_total_simulated_time()
        self.print_avg_load_factor()
        self.print_total_aircraft_throughput()
        self.print_average_aircarft_throughput()
        self.print_total_passenger_throughput()
        self.print_average_passenger_throughput()
        self.print_fato_utilization()

# def print_passenger_consolidation_time_stats(self):
#     print("Passenger consolidation time stats:")
#     print(f"Mean: {np.mean(self.passenger_consolidation_time)}")
#     print(f"Median: {np.median(self.passenger_consolidation_time)}")
#     print(f"Max: {np.max(self.passenger_consolidation_time)}")
#     print(f"Min: {np.min(self.passenger_consolidation_time)}")
#     print(f"Std: {np.std(self.passenger_consolidation_time)}")
#
#
# def save_passenger_consolidation_time_stats(self, output_dir, performance_metrics_output_file_name):
#     with open(os.path.join(output_dir, performance_metrics_output_file_name), 'w') as f:
#         f.write("Passenger consolidation time stats:\n")
#         f.write(f"Mean: {np.mean(self.passenger_consolidation_time)}\n")
#         f.write(f"Median: {np.median(self.passenger_consolidation_time)}\n")
#         f.write(f"Max: {np.max(self.passenger_consolidation_time)}\n")
#         f.write(f"Min: {np.min(self.passenger_consolidation_time)}\n")
#         f.write(f"Std: {np.std(self.passenger_consolidation_time)}\n")
#
#
# def save_performance_metrics(self, output_dir, performance_metrics_output_file_name):
#     self.save_passenger_consolidation_time_stats(output_dir, performance_metrics_output_file_name)
#
