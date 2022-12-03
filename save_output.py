import pandas as pd
import os
from utils.json_formatter import create_trajectory_json
from utils.helpers import is_shared_charger, none_checker, get_str_before_first_occurrence_of_char
import json


def save_output(trackers,
                simulation_params,
                output_dir,
                config_output_file_name,
                # aircraft_trajectory_output_file_name,
                # passenger_trajectory_output_file_name,
                # flight_schedule_output_file_name,
                performance_metrics_output_file_name):
    """
    Saves simulation configuration and sim output to a JSON file and also saves agent trajectories to csv.
    :param trackers : Dictionary of trackers
    :param simulation_params : Nested dictionary of simulation parameters
    :param output_dir : Output directory
    :param config_output_file_name : Name of the config output file
    # :param aircraft_trajectory_output_file_name : Name of the aircraft trajectory output file
    # :param passenger_trajectory_output_file_name : Name of the passenger trajectory output file
    # :param flight_schedule_output_file_name : Name of the flight schedule output file
    :param performance_metrics_output_file_name : Name of the performance metrics output file
    """
    # Create output directory if it does not exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    config_output_file_name = os.path.join(output_dir, config_output_file_name)

    config_output = {
        'sim_params': simulation_params['sim_params'],
        'network_and_demand': simulation_params['network_and_demand'],
        'vertiport_params': simulation_params['vertiport_params'],
        'passenger_params': simulation_params['passenger_params'],
        'aircraft_params': simulation_params['aircraft_params'],
        'output_params': simulation_params['output_params']
    }

    # Save simulation configuration to JSON file
    with open(config_output_file_name+'.json', 'w') as outfile:
        json.dump(config_output, outfile, indent=4)

    # Save agent trajectories to csv
    for key, value in trackers.items():
        df = pd.DataFrame.from_dict(value, orient='index')
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'time'}, inplace=True)
        trajectory_output_file_name = os.path.join(output_dir, key)
        df.to_csv(trajectory_output_file_name+'.csv')

        if key != 'flight_schedule':
            # Convert trajectory df to geoJSON and save
            agent_type = get_str_before_first_occurrence_of_char(key, '_')
            json_trajectory = create_trajectory_json(df=df, agent_type=agent_type)
            with open(trajectory_output_file_name+'.geojson', 'w') as f:
                json.dump(json_trajectory, f)




    # if not shared_charger_sets:
    #     save_folder = f"output/{layout_type}_dist_{time_aircraft_arrival_interval_parameters['distribution']}_low_{time_aircraft_arrival_interval_parameters['low']}_high_{time_aircraft_arrival_interval_parameters['high']}_scale_{time_aircraft_arrival_interval_parameters['scale']}"
    # else:
    #     save_folder = f"output/{layout_type}_dist_{time_aircraft_arrival_interval_parameters['distribution']}_low_{time_aircraft_arrival_interval_parameters['low']}_high_{time_aircraft_arrival_interval_parameters['high']}_scale_{time_aircraft_arrival_interval_parameters['scale']}"
    # os.makedirs(save_folder, exist_ok=True)
    # for key, value in trackers.items():
    #     df = pd.DataFrame.from_dict(value, orient='index')
    #     df.reset_index(inplace=True)
    #     df.rename(columns={'index': 'time'}, inplace=True)
    #     df.to_csv(f'{save_folder}/{key}_charging_{time_charging}.csv')
    #
    #     # Convert trajectory file to geoJSON and save
    #     json_trajectory = create_trajectory_json(df)
    #     with open(f'{save_folder}/{key}_charging_{time_charging}.geojson', 'w') as f:
    #         json.dump(json_trajectory, f)

    # config_output = {
    #     'layout_name': simulation_params['sim_params']['layout_name'],
    #     'num_flight_destinations': simulation_params['network_and_demand']['num_flight_destinations'],
    #     'num_aircraft': simulation_params['network_and_demand']['aircraft_arrival_process']['num_aircraft'],
    #     'num_passengers': simulation_params['network_and_demand']['passenger_arrival_process']['num_passengers'],
    #     'arrival_priority': simulation_params['sim_params']['arrival_priority'],
    #     'departure_priority': simulation_params['sim_params']['departure_priority'],
    #     'simultaneous_taxi_and_take_off': simulation_params['sim_params']['simultaneous_taxi_and_take_off'],
    #     'num_security_check_servers': simulation_params['vertiport_params']['num_security_check_servers'],
    #     'num_chargers': simulation_params['vertiport_params']['num_chargers'],
    #     'is_shared_charger': is_shared_charger(simulation_params['vertiport_params']['shared_charger_sets']),
    #
    #     'time_charging': simulation_params['aircraft_params']['time_charging'],
    #     'charging_dist': simulation_params['aircraft_params']['charging_time_dist'],
    #
    #     'is_aircraft_arrival_input': none_checker(simulation_params['network_and_demand']['aircraft_arrival_process']),
    #     'aircraft_arrival_process': simulation_params['network_and_demand']['aircraft_arrival_process'],
    #
    #     'ground_taxi_speed'
    #     'time_pre_charging_processes'
    #     'time_charging_plug_disconnection'
    #     'time_post_charging_processes'
    #     'time_descend_transition'
    #     'time_hover_descend'
    #     'time_rotor_spin_down'
    #     'time_post_landing_safety_checks'
    #     'time_tug_connection'
    #     'time_tug_disconnection'
    #     'time_pre_take_off_check_list'
    #     'time_rotor_spin_up'
    #     'time_hover_climb'
    #     'time_climb_transition'
    #
    #     'is_passenger_arrival_input'
    #     'passenger_arrival_distribution_name'
    #     'passenger_arrival_distribution_param1'
    #     'passenger_arrival_distribution_param2'
    #     'passenger_arrival_distribution_param3'
    #     'max_passenger_interarrival_time'
    #     'max_val_in_passenger_arrival_distribution'
    #     'is_randomize_passanger_time_constants'
    #
    #     'car_to_entrance_walking_time_constant'
    #     'car_to_entrance_walking_time_distribution_name'
    #     'car_to_entrance_walking_time_distribution_param1'
    #     'car_to_entrance_walking_time_distribution_param2'
    #     'car_to_entrance_walking_time_distribution_param3'
    #
    #     'security_check_walking_time_constant'
    #     'security_check_walking_time_distribution_name'
    #     'security_check_walking_time_distribution_param1'
    #     'security_check_walking_time_distribution_param2'
    #     'security_check_walking_time_distribution_param3'
    #
    #     'waiting_room_to_boarding_gate_walking_time_constant'
    #     'waiting_room_to_boarding_gate_walking_time_distribution_name'
    #     'waiting_room_to_boarding_gate_walking_time_distribution_param1'
    #     'waiting_room_to_boarding_gate_walking_time_distribution_param2'
    #     'waiting_room_to_boarding_gate_walking_time_distribution_param3'
    #
    #     'boarding_gate_to_security_check_walking_time_constant'
    #     'boarding_gate_to_security_check_walking_time_distribution_name'
    #     'boarding_gate_to_security_check_walking_time_distribution_param1'
    #     'boarding_gate_to_security_check_walking_time_distribution_param2'
    #     'boarding_gate_to_security_check_walking_time_distribution_param3'
    #
    #     'embark_disembark_time_constant'
    #     'embark_disembark_time_distribution_name'
    #     'embark_disembark_time_distribution_param1'
    #     'embark_disembark_time_distribution_param2'
    #     'embark_disembark_time_distribution_param3'
    #
    #     'deboard_aircraft_and_walk_to_exit_constant'
    #     'deboard_aircraft_and_walk_to_exit_distribution_name'
    #     'deboard_aircraft_and_walk_to_exit_distribution_param1'
    #     'deboard_aircraft_and_walk_to_exit_distribution_param2'
    #     'deboard_aircraft_and_walk_to_exit_distribution_param3'
    # }
