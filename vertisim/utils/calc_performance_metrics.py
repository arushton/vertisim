from collections import defaultdict
import numpy as np
import pandas as pd
from .units import ms_to_min

def calculate_passenger_trip_time_stats(passenger_trip_time_tracker, flight_directions):
    trip_times = defaultdict(lambda: defaultdict(dict))
    for vertiport_id, data in passenger_trip_time_tracker.items():
        waiting_times = np.array(list(data.values()))
        trip_times[vertiport_id]['passenger_trip_time']['mean'] = ms_to_min(np.mean(waiting_times))
        trip_times[vertiport_id]['passenger_trip_time']['median'] = ms_to_min(np.median(waiting_times))
        trip_times[vertiport_id]['passenger_trip_time']['std'] = ms_to_min(np.std(waiting_times))
        trip_times[vertiport_id]['passenger_trip_time']['max'] = ms_to_min(np.max(waiting_times))
        trip_times[vertiport_id]['passenger_trip_time']['min'] = ms_to_min(np.min(waiting_times))
    print("Passenger trip time statistics in minutes:")
    print("---------------------------------------------")
    df = pd.DataFrame(
        {
            'mean': trip_times[flight_direction]['passenger_trip_time']['mean'],
            'median': trip_times[flight_direction]['passenger_trip_time']['median'],
            'std': trip_times[flight_direction]['passenger_trip_time']['std'],
            'max': trip_times[flight_direction]['passenger_trip_time']['max'],
            'min': trip_times[flight_direction]['passenger_trip_time']['min']
        } for flight_direction in flight_directions
    )
    df.index = flight_directions
    print(df)
    print("")  

def calculate_passenger_waiting_time_stats(passenger_waiting_time_tracker):
    waiting_times_dict = defaultdict(lambda: defaultdict(dict))
    for vertiport_id, data in passenger_waiting_time_tracker.items():
        waiting_times = np.array(list(data.values()))
        waiting_times_dict[vertiport_id]['passenger_waiting_time']['mean'] = ms_to_min(np.mean(waiting_times))
        waiting_times_dict[vertiport_id]['passenger_waiting_time']['median'] = ms_to_min(np.median(waiting_times))
        waiting_times_dict[vertiport_id]['passenger_waiting_time']['std'] = ms_to_min(np.std(waiting_times))
        waiting_times_dict[vertiport_id]['passenger_waiting_time']['max'] = ms_to_min(np.max(waiting_times))
        waiting_times_dict[vertiport_id]['passenger_waiting_time']['min'] = ms_to_min(np.min(waiting_times))
    print("Passenger waiting time statistics in minutes:")
    print("---------------------------------------------")
    df = pd.DataFrame(
        {
            'mean': waiting_times_dict[vertiport_id]['passenger_waiting_time']['mean'],
            'median': waiting_times_dict[vertiport_id]['passenger_waiting_time']['median'],
            'std': waiting_times_dict[vertiport_id]['passenger_waiting_time']['std'],
            'max': waiting_times_dict[vertiport_id]['passenger_waiting_time']['max'],
            'min': waiting_times_dict[vertiport_id]['passenger_waiting_time']['min']
        } for vertiport_id in waiting_times_dict.keys()
    )
    print(df)
    print("---------------------------------------------")    
    print("")