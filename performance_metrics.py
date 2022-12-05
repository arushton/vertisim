import numpy as np
import pandas as pd
from utils.units import ms_to_min
from utils.helpers import nested_dict_all_values, remove_larger_keys, get_values_from_nested_dict
import matplotlib.pyplot as plt


class PerformanceMetrics:

    def __init__(self, sim_start_timestamp, passenger_consolidation_time, passenger_departure_queue_count, aircraft_arrival_queue_count,
                 aircraft_departure_queue_count, passenger_waiting_time, passenger_transfer_time, flight_schedule,
                 fato_usage_tracker):
        self.sim_start_timestamp = sim_start_timestamp
        self.passenger_consolidation_time = passenger_consolidation_time
        self.passenger_departure_queue_count = passenger_departure_queue_count
        self.aircraft_arrival_queue_count = aircraft_arrival_queue_count
        self.aircraft_departure_queue_count = aircraft_departure_queue_count
        self.passenger_waiting_time = passenger_waiting_time
        self.passenger_transfer_time = passenger_transfer_time
        self.flight_schedule = flight_schedule
        self.fato_usage_tracker = fato_usage_tracker
        self.hour = 60*60*1000

        self.aircraft_arrival_queue_count = remove_larger_keys(self.aircraft_arrival_queue_count, self.flight_schedule)

        self.print_passenger_consolidation_time_stats()
        self.print_passenger_waiting_time_stats()
        self.print_passenger_transfer_time_stats()
        self.print_passenger_departure_queue_count_stats()
        self.print_aircraft_arrival_queue_count_stats()
        self.print_aircraft_departure_queue_count_stats()
        self.print_avg_load_factor()
        self.print_total_aircraft_throughput()
        self.print_average_aircarft_throughput()
        self.print_total_passenger_throughput()
        self.print_average_passenger_throughput()
        self.print_fato_utilization()
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

    def compute_total_passenger_throughput(self):
        # Computes the total passenger throughput
        return sum(len(flight) for flight in get_values_from_nested_dict(self.flight_schedule, 'passengers'))/2

    def compute_average_passenger_throughput(self):
        # Computes the passenger throughput skipping the first 1 hour of the simulation
        total_passengers = 0
        for key, value in self.flight_schedule.items():
            if self.sim_start_timestamp + self.hour <= key <= self.sim_start_timestamp + 2*self.hour:
                total_passengers += len(self.flight_schedule[key]['passengers'])
        return total_passengers

    def compute_aircraft_throughput(self):
        return len(self.flight_schedule) / 2

    def compute_average_aircraft_throughput(self):
        # Computes the passenger throughput
        total_aircraft = 0
        for key, value in self.flight_schedule.items():
            if self.sim_start_timestamp + self.hour <= key <= self.sim_start_timestamp + 2*self.hour:
                if self.flight_schedule[key]['event'] == 'take_off':
                    total_aircraft += 1
        return total_aircraft

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

    def print_total_aircraft_throughput(self):
        print(f"Total aircraft throughput: {self.compute_aircraft_throughput()}")

    def print_average_aircarft_throughput(self):
        print(f"Average aircraft throughput in 1 hour: {self.compute_average_aircraft_throughput()}")

    def print_total_passenger_throughput(self):
        print(f"Total passenger throughput: {self.compute_total_passenger_throughput()}")

    def print_average_passenger_throughput(self):
        print(f"Average passenger throughput: {self.compute_average_passenger_throughput()}")

    def print_fato_utilization(self):
        # Sums the difference between keys when the first value is 0 and the next value is 1.
        keys = list(self.fato_usage_tracker.keys())
        values = list(self.fato_usage_tracker.values())
        time_fato_empty = 0
        for i in range(2, len(keys)-1):
            if values[i] == 0:
                if values[i+1] == 1:
                    time_fato_empty += keys[i+1] - keys[i]

        total_sim_time = keys[-1] - keys[2]
        fato_utilization = round((total_sim_time - time_fato_empty) / total_sim_time * 100, 2)
        print(f'FATO utilization: {fato_utilization}')


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
