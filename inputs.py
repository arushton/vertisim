import time
from sim_setup import sim_setup

# ------------------------ Inputs ------------------------
# Simulation parameters
# --------------------
sim_params = {
    'sim_time': 60 * 60 * 100,  # seconds
    'arrival_priority': 1,  # Lower the value higher the priority
    'departure_priority': 1,  # Lower the value higher the priority
    'simultaneous_taxi_and_take_off': True,
    'initial_parking_occupancy_%': 0,  # Initially ... % of the parking spaces are occupied with aircraft.
    'num_initial_passengers': 0,  # #of passengers at the vertiport at the beginning of the simulation.
    'random_seed': 42,
    'max_passenger_waiting_time': 60 * 10,  # seconds
    'interuptive_approach': False,   # For more details see the paper section ..., #TODO: Not implemented yet. Keep it False.
    'only_aircraft_simulation': False,   # If True, then the simulation will only simulate aircraft turnaround.
    'default_aircraft': True,  # If True, then the simulation will use the default aircraft parameters.
    'verbose': True    # If True, then the simulation will print the simulation output and performance metrics.
    # 'aircraft_assignment_rule_1': True,  # If True, then the simulator will use rule 1 for aircraft assignment. (
    #                                      # Assign the least capacity aircraft that can complete the mission)
    # 'aircraft_assignment_rule_2': False  # If True, then the simulator will use rule 2 for aircraft assignment. (
    #                                      # Fill the aircraft that can complete the mission and arrived first)
}

# Network and Trips
# -----------------
network_and_demand = {
    'vertiport_network_file_path': '/Users/eminburakonat/Google Drive/Research/UAM/8. Vertiport '
                                   'Simulation/vertiSim_dev/input/vertiport_network_full.csv',

    # DEMAND FILES.
    # ---------------------------------------------------------------
    # If these are not None, then the demand is read from these files.
    # If these are None, then the artificial demand is generated.
    # Priority is given to the demand files.
    'passenger_arrival_schedule_file_name': None,  # Use a full path. If None, passenger_arrival_generator will be used
    'aircraft_arrival_schedule_file_name': None,  # Use a full path. If None, aircraft_arrival_generator will be used.

    # ARTIFICIAL PASSENGER DEMAND GENERATION
    # --------------------------------------
    # Prob. dist. name and the parameter variable names should be consistent with the reference:
    # https://docs.scipy.org/doc/scipy/reference/stats.html. You may need to add/remove some parameters
    # depending on the distribution you use.
    'passenger_arrival_process': {
        'passenger_arrival_distribution': {
            'distribution_name': 'poisson',
            'parameters': {
                'mu': 60 * 5  # seconds
                # 'param3': None,
                # 'param4': None
            },
            'distribution_type': 'discrete',  # 'discrete' or 'continuous'
            'max_val_in_dist': 120,  # seconds  # UNUSED
            'num_passengers': 300,  # Number of passengers to be generated
        }
    },

    # ARTIFICIAL AIRCRAFT SUPPLY GENERATION
    # -------------------------------------
    'aircraft_arrival_process': {
        'aircraft_fleet_specs': {  # Aircraft names, passenger capacities, range, and battery capacities
            'jobyS4': {
                'pax': 4,
                'range': 150,  # miles
                'battery_capacity': 160,  # kWh
            }
            # 'archerMaker': {
            #     'pax': 2,
            #     'range': 60,  # miles
            #     'battery_capacity': 75,  # kWh
            # },
            # 'Heaviside': {
            #     'pax': 1,
            #     'range': 100,  # miles
            #     'battery_capacity': 23,  # kWh
            # },
            # 'liliumJet': {
            #     'pax': 6,
            #     'range': 125,  # miles
            #     'battery_capacity': 265,  # kWh
            # },
            # 'betaAlia': {
            #     'pax': 5,
            #     'range': 172,  # miles
            #     'battery_capacity': 287,  # kWh
            # }
        },
        'aircraft_arrival_distribution': {
            'distribution_name': 'poisson',
            'parameters': {
                'mu': 60 * 1  # seconds
                # 'param3': None,
                # 'param4': None
            },
            'distribution_type': 'discrete',  # 'discrete' or 'continuous'
            'max_interarrival_time': 180,  # seconds
            'num_aircraft': 300,  # Number of aircraft in the simulation. If None, then the required number of aircraft
            # will be estimated from the num_passengers.
            'num_passengers': None,  # If num_aircraft is defined, this can be None because num_aircraft will overwrite.
            'min_init_soc': 20,  # Minimum initial SOC of the aircraft at the arrival to the vertiport
            'max_init_soc': 50,  # Maximum initial SOC of the aircraft at the arrival to the vertiport
        }
    }
}


# Vertiport parameters
# --------------------
vertiport_params = {
    'vertiport_layout_file_path': '/Users/eminburakonat/Google Drive/Research/UAM/8. Vertiport '
                                  'Simulation/vertiSim_dev/input/skyport_layouts/skyport_layout.xls',
    'layout': 'clover_1_fato_4_park',
    'num_security_check_servers': 12,
    'num_chargers': 4,
    'charger_max_charge_rate': 480,  # kW # TODO: Utilize this parameter when creating battery model.
    'charger_efficiency': 0.90,
    'shared_charger_sets': None
    # # Note: PARK IDs should match with the excel/csv file PARK IDs.
    # shared_charger_sets = {
    #     1: ['PARK11', 'PARK12'],
    #     2: ['PARK12', 'PARK13'],
    #     3: ['PARK13', 'PARK14']
    # },
}

# Passenger parameters
# --------------------
# Time parameters should be a constant or a distribution. One should be None, the other should be provided.
passenger_params = {
    'randomize_constants': True,  # If true, the constants will be randomized. If false, the constants will be used as
    # it is.
    'car_to_entrance_walking_time_constant': 40,  # secs
    'car_to_entrance_walking_time_dist': None,
    'security_check_time_constant': 20,  # secs
    'security_check_time_dist': None,
    # 'security_check_time_dist': {
    #     'distribution_name': 'expon',
    #     'parameters': {
    #         'loc': 0,
    #         'scale': 1
    #         # 'param3': None,
    #         # 'param4': None
    #     },
    #     'max_val_in_dist': 60
    # },
    'waiting_room_to_boarding_gate_walking_time_constant': 30,  # secs
    'waiting_room_to_boarding_gate_walking_time_dist': None,
    'boarding_gate_to_aircraft_time_constant': 60,  # secs
    'boarding_gate_to_aircraft_time_dist': None,
    'embark_disembark_time_constant': 60 * 3,  # secs
    'embark_disembark_time_dist': None,
    'deboard_aircraft_and_walk_to_exit_constant': 120,  # secs
    'deboard_aircraft_and_walk_to_exit_dist': None,
}

# Aircraft parameters
# -------------------
aircraft_params = {
    # DEFAULT AIRCRAFT PARAMETERS
    'aircraft_model': 'jobyS4',  # This is the default aircraft type, if aircraft type is given with the schedule,
    # then that will be used as the aircraft type.
    'pax': 4,  # Default passenger capacity, if passenger capacity is given with the schedule,
    # then that will be used as the passenger capacity.
    'range': 150,  # miles
    'initial_soc': 20,  # Default initial SOC of aircraft at the arrival to the vertiport

    # TAKE-OFF, LANDING, AND TURNAROUND TIME PARAMETERS
    # ------------------------------------------------
    'ground_taxi_speed': 3.67,  # ft/s
    'time_passenger_embark_disembark': 60 * 4,  # secs
    'time_pre_charging_processes': 120,  # sec
    'time_charging_plug_disconnection': 0,  # sec
    'time_post_charging_processes': 120,  # sec
    'time_descend_transition': 30,  # sec
    'time_hover_descend': 10,  # sec
    'time_rotor_spin_down': 5,  # sec
    'time_post_landing_safety_checks': 15,  # sec
    'time_tug_connection': 0,  # sec
    'time_tug_disconnection': 0,  # sec
    'time_pre_take_off_check_list': 15,  # sec
    'time_rotor_spin_up': 5,  # sec
    'time_hover_climb': 10,  # sec
    'time_climb_transition': 30,  # sec

    # AIRCRAFT CHARGING TIME PARAMETERS
    # ----------------------------
    # There are 3 options to simulate the charging time of an aircraft:
    # 1. Constant charging time defined by 'time_charging' parameter.
    # 2. Charging time distribution defined by 'time_charging_dist' parameter.
    # 3. Based on energy requirement to complete the mission. Each aircraft type has a different energy requirement to
    # complete the mission. To use this feature, battery model parameters and aircraft energy consumption data need to
    # be given. The energy requirement is computed with the model that Sridhar et. al. developed. TODO: Add link

    'time_charging': None,  # constant sec  # If None charging_time_dist will be used.
    # Prob. dist. name and the parameter variable names should be consistent with the reference:
    # https://docs.scipy.org/doc/scipy/reference/stats.html. You may need to add/remove some parameters
    # depending on the distribution you use.
    'charging_time_dist': {
        'distribution_name': 'poisson',
        'parameters': {
            'mu': 60 * 5
            # 'param3': None,
            # 'param4': None
        },
        'distribution_type': 'discrete',  # 'discrete' or 'continuous'
        'max_charge_duration': 60 * 30,  # sec. This parameter is used as the max charge time for the charging
        # time distribution generation.
    },
    'aircraft_energy_consumption_data_folder_path': '/Users/eminburakonat/Google Drive/Research/UAM/8. Vertiport '
                                                  'Simulation/vertiSim_dev/input/aircraft_energy_consumption',
    'min_reserve_soc': 20  # %  # This is the minimum acceptable SoC that the aircraft should have at the end of the mission.
}

output_params = {
    'output_folder_path': '/Users/eminburakonat/Google Drive/Research/UAM/8. Vertiport Simulation/vertiSim_dev/output',
    'config_output_file_name': 'config',
    # 'aircraft_trajectory_output_file_name': 'aircraft_agent_trajectory',
    # 'passenger_trajectory_output_file_name': 'passenger_agent_trajectory',
    # 'flight_schedule_output_file_name': 'flight_schedule',
    'performance_metrics_output_file_name': 'performance_metrics'
}

# ----------------------------------------------------------
start_time = time.time()

sim_setup(sim_params=sim_params,
          network_and_demand=network_and_demand,
          vertiport_params=vertiport_params,
          passenger_params=passenger_params,
          aircraft_params=aircraft_params,
          output_params=output_params,
          sim_start_time=start_time
          )
