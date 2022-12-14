# ------------------------ Inputs ------------------------
# Simulation parameters
# --------------------
sim_params = {
    'sim_time': 60 * 60 * 100,  # seconds
    'arrival_priority': 1,  # Lower the value higher the priority
    'departure_priority': 1,  # Lower the value higher the priority
    'simultaneous_taxi_and_take_off': True,
    'initial_parking_occupancy_%': 0,   # Initially ... % of the parking spaces are occupied with aircraft.
    'num_initial_passengers': 0,   # #of passengers at the vertiport at the beginning of the simulation.
    'random_seed': 42,
}

# Network and Trips
# -----------------
network_and_demand = {
    'vertiport_network_file_name': 'input/vertiport_network.csv',
    'passenger_schedule_file_name': 'input/trips.csv',
    'aircraft_arrival_schedule': None,  # If fixed schedule, input a list of integers for interarrival times with a
    # size of num_aircraft or input a csv file path.
    'aircraft_arrival_distribution': { # Prob. dist. name and the parameters should be consistent with
        # the reference: https://docs.scipy.org/doc/scipy/reference/stats.html. If param is not used put None.
        'distribution': 'expon',
        'param1': 1,
        'param2': 1,
        'param3': None,
        'param4': None,
        'param5': None
    }
}

# Vertiport parameters
# --------------------
vertiport_params = {
    'vertiport_layout_file_name': 'skyport_layouts/skyport_layout.xls',
    'layout': 'clover_1_fato_4_park',
    'num_chargers': 4,
    'shared_charger_sets': None,
# # Note: PARK IDs should match with the excel/csv file PARK IDs.
# shared_charger_sets = {
#     1: ['PARK11', 'PARK12'],
#     2: ['PARK12', 'PARK13'],
#     3: ['PARK13', 'PARK14']
# },
    'num_security_check_servers': 3
}


# Passenger parameters
# --------------------
# Time parameters should be a constant or a distribution. One should be None, the other should be provided. If both None
# default values will be used.
passenger_params = {
    'car_to_entrance_walking_time_constant': 40,  # secs
    'car_to_entrance_walking_time_dist': None,
    'security_check_time_constant': None,  # secs
    'security_check_time_dist': {
        'distribution': 'expon',
        'param1': 5,
        'param2': 2,
        'param3': None,
        'param4': None,
        'param5': None
    },
    'boarding_gate_to_aircraft_time_constant': 90,  # secs
    'boarding_gate_to_aircraft_time_dist': None,
    'embark_disembark_time_constant': 60 * 4.5,  # secs
    'embark_disembark_time_dist': None,
    'deboard_aircraft_and_walk_to_exit_constant': 120,   # secs
    'deboard_aircraft_and_walk_to_exit_dist': None,
    'passenger_walk_speed': 4.6  # ft/s
}


# Aircraft parameters
# --------------------
aircraft_params = {
    'aircraft_type': 'jobyS4',
    'aircraft_capacity': 4,
    'ground_taxi_speed': 5,  # ft/s
    'time_pre_charging_processes': 128,  # sec
    'time_charging_plug_disconnection': 21,  # sec
    'time_post_charging_processes': 152,  # sec
    'time_descend_transition': 40,  # sec
    'time_hover_descend': 20,  # sec
    'time_rotor_spin_down': 5,  # sec
    'time_post_landing_safety_checks': 15,  # sec
    'time_tug_connection': 30,  # sec
    'time_tug_disconnection': 30,  # sec
    'time_pre_take_off_check_list': 30,  # sec
    'time_rotor_spin_up': 5,  # sec
    'time_hover_climb': 12,  # sec
    'time_climb_transition': 30  # sec
}

output_params = {
    'save_folder_path': 'outputs'
}