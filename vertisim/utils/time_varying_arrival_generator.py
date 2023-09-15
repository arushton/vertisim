import numpy as np
import pandas as pd

def get_arrival_rates(df):
    # Initialize an empty dictionary to hold the rates
    rate_dict = {}
    
    # Populate the dictionary
    for col in df.columns:
        if col != 'time_sec':
            origin, destination = col.split('_')
            if origin not in rate_dict:
                rate_dict[origin] = {}
            rate_dict[origin][destination] = list(df[col])
    
    time_intervals = list(df['time_sec'])
    return rate_dict, time_intervals


def generate_arrival_times(arrival_rate_df, origin, target_count):
    # Get the arrival rates and time intervals
    rate_dict, time_intervals = get_arrival_rates(arrival_rate_df)
    print(f"Generating arrival times for origin vertiport {origin}...")

    destinations = list(rate_dict[origin].keys())
    results = []

    for destination in destinations:
        current_time = 0
        total_generated = 0
        arrival_times = []

        rates = rate_dict[origin][destination]
        for rate in rates:
            num_to_generate = int(rate * target_count / sum(rates))

            for _ in range(num_to_generate):
                # Generate a time for this arrival using the exponential distribution
                time_to_next = np.random.exponential(1 / rate) * 3600  # in seconds

                # Add this time to the current time to get the arrival time
                current_time += time_to_next

                # Append this time to the list of arrival times
                arrival_times.append({
                    'passenger_arrival_time': current_time,
                    'origin_vertiport_id': origin,
                    'destination_vertiport_id': destination
                })

                total_generated += 1

        # Add generated data for this destination to results
        results.extend(arrival_times)

    # Sort the list based on time
    results = sorted(results, key=lambda x: x['passenger_arrival_time'])

    return pd.DataFrame(results)