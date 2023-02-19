from loop_input import *
import itertools
from tqdm.contrib.itertools import product


def run_vertisim():
    # passenger_arrival_process = [15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180]  # [30, 60, 120, 180] # [15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180]  # [30, 60, 120, 180]
    passenger_arrival_process = [15]
    # aircraft_arrival_process = [150]
    aircraft_arrival_process = [60 / (12 / 60)] #, 60 / (7 / 60), 60 / (8 / 60), 60 / (9 / 60), 60 / (10 / 60),
                                # 60 / (11 / 60), 60 / (14 / 60), 60 / (15 / 60), 60 / (16 / 60),
                                # 60 / (17 / 60), 60 / (18 / 60), 60 / (19 / 60), 60 / (20 / 60), 60 / (21 / 60),
                                # 60 / (22 / 60), 60 / (23 / 60), 60 / (24 / 60), 60 / (25 / 60), 60 / (30 / 60),
                                # 60 / (40 / 60), 60 / (48 / 60)] # [45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 195, 210, 225, 240, 255, 270, 285, 300]  # [60, 120, 180, 240, 300] [45, 75, 90, 105, 135, 150, 210]
    max_passenger_waiting_time = [600]
    charging_time = [60 * 12]
    # layouts = ['clover_1_fato_4_park']
    layouts = ['clover_1_fato_1_park', 'clover_1_fato_2_park', 'clover_1_fato_3_park', 'clover_1_fato_4_park',
               'clover_1_fato_5_park', 'clover_1_fato_6_park', 'clover_1_fato_7_park', 'clover_1_fato_8_park',
               'clover_1_fato_9_park', 'clover_1_fato_10_park']
    only_aircraft_sim = True
    for passenger_arrival, aircraft_arrival_mu, waiting_time_threshold, charge_time, vertiport_layout in \
            product(passenger_arrival_process, aircraft_arrival_process, max_passenger_waiting_time, charging_time, layouts):
        # print("Running simulation for: ", vertiport_layout, " with passenger arrival mu: ",
        #       passenger_arrival_mu, " aircraft arrival mu: ", aircraft_arrival_mu,
        #       " waiting time threshold: ", waiting_time_threshold, " charging time: ", charge_time)
        # Run the simulation
        loop_input(0, aircraft_arrival_mu,
                   waiting_time_threshold, charge_time, vertiport_layout, only_aircraft_sim)


if __name__ == '__main__':
    start_time = time.time()
    run_vertisim()
    end_time = time.time()
    time_taken = end_time - start_time
    print(f'Total time to run experiments: {round(time_taken, 2)} seconds')