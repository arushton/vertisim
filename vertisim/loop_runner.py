from loop_input import *
import itertools
from tqdm.contrib.itertools import product


def run_vertisim():
    passenger_arrival_process = [90, 105, 135]  # [30, 60, 120, 180]
    aircraft_arrival_process = [45, 75, 90, 105, 135, 150, 210]  # [60, 120, 180, 240, 300]
    max_passenger_waiting_time = [600]
    charging_time = [60 * 5, 60 * 7, 60 * 10, 60 * 15]
    layouts = ['clover_1_fato_1_park', 'clover_1_fato_2_park', 'clover_1_fato_3_park', 'clover_1_fato_4_park',
               'clover_1_fato_5_park', 'clover_1_fato_6_park', 'clover_1_fato_7_park', 'clover_1_fato_8_park']
    only_aircraft_sim = False
    for passenger_arrival_mu, aircraft_arrival_mu, waiting_time_threshold, charge_time, vertiport_layout in \
            product(passenger_arrival_process, aircraft_arrival_process, max_passenger_waiting_time, charging_time, layouts):
        # print("Running simulation for: ", vertiport_layout, " with passenger arrival mu: ",
        #       passenger_arrival_mu, " aircraft arrival mu: ", aircraft_arrival_mu,
        #       " waiting time threshold: ", waiting_time_threshold, " charging time: ", charge_time)
        # Run the simulation
        loop_input(passenger_arrival_mu, aircraft_arrival_mu,
                   waiting_time_threshold, charge_time, vertiport_layout, only_aircraft_sim)

    # only_aircraft_sim = True
    # for aircraft_arrival_mu, waiting_time_threshold, charge_time, vertiport_layout in \
    #         itertools.product(passenger_arrival_process, aircraft_arrival_process, max_passenger_waiting_time,
    #                           charging_time, layouts):
    #     print("Running simulation for: ", vertiport_layout, " aircraft arrival mu: ", aircraft_arrival_mu,
    #           " waiting time threshold: ", waiting_time_threshold, " charging time: ", charge_time)
    #     # Run the simulation
    #     loop_input(aircraft_arrival_mu,
    #                waiting_time_threshold, charge_time, vertiport_layout, only_aircraft_sim)


if __name__ == '__main__':
    start_time = time.time()
    run_vertisim()
    end_time = time.time()
    time_taken = end_time - start_time
    print(f'Total time to run experiments: {round(time_taken, 2)} seconds')
