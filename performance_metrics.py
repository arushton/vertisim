import numpy as np
import pandas as pd
from utils.units import ms_to_min
from utils.helpers import nested_dict_all_values, remove_larger_keys, get_values_from_nested_dict
import matplotlib.pyplot as plt


class PerformanceMetrics:

    def __init__(self, passenger_consolidation_time, passenger_departure_queue_count, aircraft_arrival_queue_count,
                 aircraft_departure_queue_count, passenger_waiting_time, passenger_transfer_time, flight_schedule):
        self.passenger_consolidation_time = passenger_consolidation_time
        self.passenger_departure_queue_count = passenger_departure_queue_count
        self.aircraft_arrival_queue_count = aircraft_arrival_queue_count
        self.aircraft_departure_queue_count = aircraft_departure_queue_count
        self.passenger_waiting_time = passenger_waiting_time
        self.passenger_transfer_time = passenger_transfer_time
        self.flight_schedule = flight_schedule

        self.aircraft_arrival_queue_count = remove_larger_keys(self.aircraft_arrival_queue_count, self.flight_schedule)

        self.print_passenger_consolidation_time_stats()
        self.print_passenger_waiting_time_stats()
        self.print_passenger_transfer_time_stats()
        self.print_passenger_departure_queue_count_stats()
        self.print_aircraft_arrival_queue_count_stats()
        self.print_aircraft_departure_queue_count_stats()
        self.print_avg_load_factor()
        # print("passenger_consolidation_time: ", self.passenger_consolidation_time)
        # print("passenger_departure_queue_count: ", self.passenger_departure_queue_count)
        # print("aircraft_arrival_queue_count: ", self.aircraft_arrival_queue_count)
        # print("aircraft_departure_queue_count: ", self.aircraft_departure_queue_count)
        # print("passenger_waiting_time: ", self.passenger_waiting_time)
        # print("passenger_transfer_time: ", self.passenger_transfer_time)
        # print("flight_schedule: ", self.flight_schedule)
        # self.plot_aircraft_arrival_queue_count()

    def calculate_passenger_consolidation_time_stats(self):
        # Creates a dataframe for passenger consolidation time statistics including mean, median, standard deviation,
        # max and min
        consolidation_times = [x['consolidation_time'] for x in list(nested_dict_all_values(self.passenger_consolidation_time, 1))]
        return pd.DataFrame(
            {
                'mean': [round(ms_to_min(np.mean(consolidation_times)), 2)],
                'median': [round(ms_to_min(np.median(consolidation_times)), 2)],
                'std': [round(ms_to_min(np.std(consolidation_times)), 2)],
                'max': [round(ms_to_min(np.max(consolidation_times)), 2)],
                'min': [round(ms_to_min(np.min(consolidation_times)), 2)]
            }
        )

    def calculate_passenger_departure_queue_count_stats(self):
        return pd.DataFrame(
            {
                'mean': [round(np.mean(list(self.passenger_departure_queue_count.values())))],
                'median': [round(np.median(list(self.passenger_departure_queue_count.values())))],
                'std': [round(np.std(list(self.passenger_departure_queue_count.values())))],
                'max': [round(np.max(list(self.passenger_departure_queue_count.values())))],
                'min': [round(np.min(list(self.passenger_departure_queue_count.values())))]
            }
        )

    def calculate_aircraft_arrival_queue_count_stats(self):
        return pd.DataFrame(
            {
                'mean': [round(np.mean(list(self.aircraft_arrival_queue_count.values())))],
                'median': [round(np.median(list(self.aircraft_arrival_queue_count.values())))],
                'std': [round(np.std(list(self.aircraft_arrival_queue_count.values())))],
                'max': [round(np.max(list(self.aircraft_arrival_queue_count.values())))],
                'min': [round(np.min(list(self.aircraft_arrival_queue_count.values())))]
            }
        )

    def calculate_aircraft_departure_queue_count_stats(self):
        return pd.DataFrame(
            {
                'mean': [round(np.mean(list(self.aircraft_departure_queue_count.values())))],
                'median': [round(np.median(list(self.aircraft_departure_queue_count.values())))],
                'std': [round(np.std(list(self.aircraft_departure_queue_count.values())))],
                'max': [round(np.max(list(self.aircraft_departure_queue_count.values())))],
                'min': [round(np.min(list(self.aircraft_departure_queue_count.values())))]
            }
        )

    def calculate_passenger_waiting_time_stats(self):
        # Creates a dataframe for passenger waiting time statistics including mean, median, standard deviation,
        # max and min

        waiting_times = [x['waiting_time'] for x in list(nested_dict_all_values(self.passenger_waiting_time, 1))]
        return pd.DataFrame(
            {
                'mean': [round(ms_to_min(np.mean(waiting_times)), 2)],
                'median': [round(ms_to_min(np.median(waiting_times)), 2)],
                'std': [round(ms_to_min(np.std(waiting_times)), 2)],
                'max': [round(ms_to_min(np.max(waiting_times)), 2)],
                'min': [round(ms_to_min(np.min(waiting_times)), 2)]
            }
        )

    def calculate_passenger_transfer_time_stats(self):
        # Creates a dataframe for passenger transfer time statistics including mean, median, standard deviation,
        # max and min

        transfer_times = [x['transfer_time'] for x in list(nested_dict_all_values(self.passenger_transfer_time, 1))]
        return pd.DataFrame(
            {
                'mean': [round(ms_to_min(np.mean(transfer_times)), 2)],
                'median': [round(ms_to_min(np.median(transfer_times)), 2)],
                'std': [round(ms_to_min(np.std(transfer_times)), 2)],
                'max': [round(ms_to_min(np.max(transfer_times)), 2)],
                'min': [round(ms_to_min(np.min(transfer_times)), 2)]
            }
        )

    def plot_aircraft_arrival_queue_count(self):
        # Plots aircraft arrival queue count
        plt.plot(list(self.aircraft_arrival_queue_count.keys()), list(self.aircraft_arrival_queue_count.values()))
        plt.xlabel('Time (min)')
        plt.ylabel('Aircraft Arrival Queue Count')
        plt.title('Aircraft Arrival Queue Count Over Time')
        plt.show()

    def compute_avg_load_factor(self):
        # Computes the average load factor of all aircraft
        flight_list = get_values_from_nested_dict(self.flight_schedule, 'passengers')
        total_passengers = sum(len(flight) for flight in flight_list)
        return total_passengers / len(flight_list)

    def print_passenger_consolidation_time_stats(self):
        print("Passenger consolidation time statistics in minutes:")
        print("-----------------------------")
        print(self.calculate_passenger_consolidation_time_stats())
        print("")

    def print_passenger_waiting_time_stats(self):
        print("Passenger waiting time statistics in minutes:")
        print("-----------------------------")
        print(self.calculate_passenger_waiting_time_stats())
        print("")

    def print_passenger_transfer_time_stats(self):
        print("Passenger transfer time statistics in minutes:")
        print("-----------------------------")
        print(self.calculate_passenger_transfer_time_stats())
        print("")

    def print_passenger_departure_queue_count_stats(self):
        print("Passenger departure queue count statistics:")
        print("-----------------------------")
        print(self.calculate_passenger_departure_queue_count_stats())
        print("")

    def print_aircraft_arrival_queue_count_stats(self):
        print("Aircraft arrival queue count statistics:")
        print("-----------------------------")
        print(self.calculate_aircraft_arrival_queue_count_stats())
        print("")

    def print_aircraft_departure_queue_count_stats(self):
        print("Aircraft departure queue count statistics:")
        print("-----------------------------")
        print(self.calculate_aircraft_departure_queue_count_stats())
        print("")

    def print_avg_load_factor(self):
        print(f"Average load factor: {round(self.compute_avg_load_factor(), 2)}")
        print("")

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
