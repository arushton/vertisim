import pandas as pd
import os
from utils.json_formatter import create_trajectory_json
from utils.helpers import is_shared_charger, none_checker, get_str_before_first_occurrence_of_char, find_first_int, \
    find_second_int
import json
import sqlite3


def save_output(trackers,
                simulation_params,
                output_dir,
                config_output_file_name,
                # aircraft_trajectory_output_file_name,
                # passenger_trajectory_output_file_name,
                # flight_schedule_output_file_name,
                performance_metrics_output_file_name,
                performance_metrics,
                sim_id):
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
        'passenger_params': simulation_params['passenger_params'],
        'aircraft_params': simulation_params['aircraft_params'],
        'output_params': simulation_params['output_params']
    }

    if simulation_params['sim_params']['verbose']:
        # Save simulation configuration to JSON file
        with open(config_output_file_name + '.json', 'w') as outfile:
            json.dump(config_output, outfile, indent=4)

        # Save agent trajectories to csv
        for key, value in trackers.items():
            df = pd.DataFrame.from_dict(value, orient='index')
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'time'}, inplace=True)
            trajectory_output_file_name = os.path.join(output_dir, key)
            df.to_csv(trajectory_output_file_name + '.csv')

            if key != 'flight_schedule' and simulation_params['sim_params']['save_trajectories']:
                # Convert trajectory df to geoJSON and save
                agent_type = get_str_before_first_occurrence_of_char(key, '_')
                if json_trajectory := create_trajectory_json(
                        df=df, agent_type=agent_type,
                        only_aircraft_simulation=simulation_params['sim_params']['only_aircraft_simulation']
                ):
                    with open(trajectory_output_file_name + '.geojson', 'w') as f:
                        json.dump(json_trajectory, f)

    # Save performance metrics to SQLite Database
    if performance_metrics:
        performance_metrics_output_file_name = os.path.join(output_dir, performance_metrics_output_file_name)
        conn = sqlite3.connect(performance_metrics_output_file_name + '.db')
        c = conn.cursor()

        # Create table
        c.execute('''CREATE TABLE IF NOT EXISTS performance_metrics
        (sim_id TEXT,
        arrival_priority INTEGER, 
        departure_priority INTEGER, 
        simultaneous_taxi_and_take_off INTEGER,
        only_aircraft_simulation INTEGER, 
        max_passenger_waiting_time_threshold REAL, 
        passenger_schedule_file_name,
        randomize_passenger_constants INTEGER, 
        car_to_entrance_walking_time_constant REAL, 
        security_check_time_constant REAL,
        waiting_room_to_boarding_gate_walking_time_constant REAL, 
        boarding_gate_to_aircraft_time_constant REAL,
        embark_disembark_time_constant REAL, 
        passenger_arrival_process_param REAL, 
        num_passengers INTEGER, 
        aircraft_schedule_file_name, 
        aircraft_arrival_process_param REAL, 
        num_aircraft INTEGER, 
        aircraft_model TEXT, 
        aircraft_pax INTEGER, 
        aircraft_range INTEGER, 
        aircraft_battery_capacity INTEGER, 
        ground_taxi_speed REAL,
        time_passenger_embark_disembark REAL, 
        time_pre_charging_processes REAL, 
        time_charging_plug_disconnection REAL,
        time_post_charging_processes REAL, 
        time_descend_transition REAL, 
        time_hover_descend REAL, 
        time_rotor_spin_down REAL,
        time_post_landing_safety_checks REAL, 
        time_tug_connection REAL, 
        time_tug_disconnection REAL, 
        time_pre_take_off_check_list REAL, 
        time_rotor_spin_up REAL, 
        time_hover_climb REAL, 
        time_climb_transition REAL,
        time_charging, 
        charging_time_param_distribution TEXT, 
        charging_time_param_mu REAL, 
        tlof_time REAL,
        average_charge_time REAL,
        average_taxi_time REAL,
        average_aircraft_turnaround_time REAL,
        vertiport_layout TEXT,
        mean_passenger_consolidation_time REAL, 
        max_passenger_consolidation_time REAL, 
        min_passenger_consolidation_time REAL, 
        mean_passenger_waiting_time REAL, 
        max_passenger_waiting_time REAL, 
        min_passenger_waiting_time REAL,
        mean_passenger_departure_queue_count REAL, 
        max_passenger_departure_queue_count INTEGER,
        min_passenger_departure_queue_count INTEGER,
        mean_pass_dep_queue_waiting_time REAL,
        max_pass_dep_queue_waiting_time REAL,
        min_pass_dep_queue_waiting_time REAL,
        mean_aircraft_arrival_queue_count REAL, 
        max_aircraft_arrival_queue_count INTEGER, 
        min_aircraft_arrival_queue_count INTEGER,
        mean_aircraft_departure_queue_count REAL, 
        max_aircraft_departure_queue_count INTEGER, 
        min_aircraft_departure_queue_count INTEGER,
        mean_aircraft_holding_time REAL,
        max_aircraft_holding_time REAL,
        min_aircraft_holding_time REAL,
        mean_load_factor REAL, 
        max_load_factor REAL, 
        min_load_factor REAL, 
        mean_aircraft_throughput REAL, 
        total_aircraft_throughput INTEGER,
        mean_passenger_throughput REAL, 
        total_passenger_throughput INTEGER, 
        fato_utilization REAL,
        passenger_interarrival_constant,
        aircraft_interarrival_constant,
        mean_aircraft_idle_time REAL,
        max_aircraft_idle_time REAL,
        min_aircraft_idle_time REAL,
        mean_passenger_trasfer_time REAL,
        max_passenger_trasfer_time REAL,
        min_passenger_trasfer_time REAL,
        total_simulated_time REAL
        )''')

        if simulation_params['sim_params']['only_aircraft_simulation'] and simulation_params['aircraft_params']['time_charging']:
            values = [(sim_id,
                    simulation_params['sim_params']['arrival_priority'],
                    simulation_params['sim_params']['departure_priority'],
                    simulation_params['sim_params']['simultaneous_taxi_and_take_off'],
                    simulation_params['sim_params']['only_aircraft_simulation'],
                    simulation_params['sim_params']['max_passenger_waiting_time'],
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                        -1,
                        -1,
                        -1,
                        -1,        
                    simulation_params['network_and_demand']['aircraft_schedule_file_name'],
                    simulation_params['network_and_demand']['aircraft_arrival_process']['aircraft_arrival_distribution'][
                        'parameters']['scale'],
                    simulation_params['network_and_demand']['aircraft_arrival_process']['num_aircraft'],
                    simulation_params['aircraft_params']['aircraft_model'],
                    simulation_params['aircraft_params']['pax'],
                    simulation_params['aircraft_params']['range'],
                    simulation_params['network_and_demand']['aircraft_arrival_process']['aircraft_fleet_specs'][
                        'jobyS4']['battery_capacity'],
                    simulation_params['aircraft_params']['ground_taxi_speed'],
                    simulation_params['aircraft_params']['time_passenger_embark_disembark'],
                    simulation_params['aircraft_params']['time_pre_charging_processes'],
                    simulation_params['aircraft_params']['time_charging_plug_disconnection'],
                    simulation_params['aircraft_params']['time_post_charging_processes'],
                    simulation_params['aircraft_params']['time_descend_transition'],
                    simulation_params['aircraft_params']['time_hover_descend'],
                    simulation_params['aircraft_params']['time_rotor_spin_down'],
                    simulation_params['aircraft_params']['time_post_landing_safety_checks'],
                    simulation_params['aircraft_params']['time_tug_connection'],
                    simulation_params['aircraft_params']['time_tug_disconnection'],
                    simulation_params['aircraft_params']['time_pre_take_off_check_list'],
                    simulation_params['aircraft_params']['time_rotor_spin_up'],
                    simulation_params['aircraft_params']['time_hover_climb'],
                    simulation_params['aircraft_params']['time_climb_transition'],
                    simulation_params['aircraft_params']['time_charging'],
                    -1,
                    -1,
                    performance_metrics['tlof_time'],
                    performance_metrics['average_charge_time'],
                    performance_metrics['average_taxi_time'],
                    performance_metrics['average_aircraft_turnaround_time'],
                    simulation_params['vertiport_params']['layout'],
                    # find_first_int(simulation_params['vertiport_params']['layout']),
                    # find_second_int(simulation_params['vertiport_params']['layout']),
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    performance_metrics['aircraft_arrival_queue_count']['mean'],
                    performance_metrics['aircraft_arrival_queue_count']['max'],
                    performance_metrics['aircraft_arrival_queue_count']['min'],
                    performance_metrics['aircraft_departure_queue_count']['mean'],
                    performance_metrics['aircraft_departure_queue_count']['max'],
                    performance_metrics['aircraft_departure_queue_count']['min'],
                    performance_metrics['aircraft_holding_times']['mean'],
                    performance_metrics['aircraft_holding_times']['max'],
                    performance_metrics['aircraft_holding_times']['min'],
                    -1,
                    -1,
                    -1,
                    performance_metrics['aircraft_throughput']['mean'],
                    performance_metrics['aircraft_throughput']['total'],
                    -1,
                    -1,
                    performance_metrics['fato_utilization'],
                    -1,
                    simulation_params['network_and_demand']['aircraft_arrival_process']['aircraft_interarrival_constant'],
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    performance_metrics['total_simulated_time'])]
        elif simulation_params['sim_params']['only_aircraft_simulation']:
            values = [(sim_id,
                    simulation_params['sim_params']['arrival_priority'],
                    simulation_params['sim_params']['departure_priority'],
                    simulation_params['sim_params']['simultaneous_taxi_and_take_off'],
                    simulation_params['sim_params']['only_aircraft_simulation'],
                    simulation_params['sim_params']['max_passenger_waiting_time'],
                    simulation_params['network_and_demand']['passenger_schedule_file_name'],
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    simulation_params['network_and_demand']['aircraft_schedule_file_name'],
                    simulation_params['network_and_demand']['aircraft_arrival_process']['aircraft_arrival_distribution'][
                        'parameters']['scale'],
                    simulation_params['network_and_demand']['aircraft_arrival_process']['num_aircraft'],
                    simulation_params['aircraft_params']['aircraft_model'],
                    simulation_params['aircraft_params']['pax'],
                    simulation_params['aircraft_params']['range'],
                    simulation_params['network_and_demand']['aircraft_arrival_process']['aircraft_fleet_specs'][
                        'jobyS4']['battery_capacity'],
                    simulation_params['aircraft_params']['ground_taxi_speed'],
                    simulation_params['aircraft_params']['time_passenger_embark_disembark'],
                    simulation_params['aircraft_params']['time_pre_charging_processes'],
                    simulation_params['aircraft_params']['time_charging_plug_disconnection'],
                    simulation_params['aircraft_params']['time_post_charging_processes'],
                    simulation_params['aircraft_params']['time_descend_transition'],
                    simulation_params['aircraft_params']['time_hover_descend'],
                    simulation_params['aircraft_params']['time_rotor_spin_down'],
                    simulation_params['aircraft_params']['time_post_landing_safety_checks'],
                    simulation_params['aircraft_params']['time_tug_connection'],
                    simulation_params['aircraft_params']['time_tug_disconnection'],
                    simulation_params['aircraft_params']['time_pre_take_off_check_list'],
                    simulation_params['aircraft_params']['time_rotor_spin_up'],
                    simulation_params['aircraft_params']['time_hover_climb'],
                    simulation_params['aircraft_params']['time_climb_transition'],
                    simulation_params['aircraft_params']['time_charging'],
                    simulation_params['aircraft_params']['charging_time_dist']['distribution_name'],
                    simulation_params['aircraft_params']['charging_time_dist']['parameters']['scale'],
                    performance_metrics['tlof_time'],
                    performance_metrics['average_charge_time'],
                    performance_metrics['average_taxi_time'],
                    performance_metrics['average_aircraft_turnaround_time'],
                    simulation_params['vertiport_params']['layout'],
                    # find_first_int(simulation_params['vertiport_params']['layout']),
                    # find_second_int(simulation_params['vertiport_params']['layout']),
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    performance_metrics['aircraft_arrival_queue_count']['mean'],
                    performance_metrics['aircraft_arrival_queue_count']['max'],
                    performance_metrics['aircraft_arrival_queue_count']['min'],
                    performance_metrics['aircraft_departure_queue_count']['mean'],
                    performance_metrics['aircraft_departure_queue_count']['max'],
                    performance_metrics['aircraft_departure_queue_count']['min'],
                    performance_metrics['aircraft_holding_times']['mean'],
                    performance_metrics['aircraft_holding_times']['max'],
                    performance_metrics['aircraft_holding_times']['min'],
                    -1,
                    -1,
                    -1,
                    performance_metrics['aircraft_throughput']['mean'],
                    performance_metrics['aircraft_throughput']['total'],
                    -1,
                    -1,
                    performance_metrics['fato_utilization'],
                    -1,
                    simulation_params['network_and_demand']['aircraft_arrival_process']['aircraft_interarrival_constant'],
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    performance_metrics['total_simulated_time'])]
        else:
            values = [(sim_id,
                    simulation_params['sim_params']['arrival_priority'],
                    simulation_params['sim_params']['departure_priority'],
                    simulation_params['sim_params']['simultaneous_taxi_and_take_off'],
                    simulation_params['sim_params']['only_aircraft_simulation'],
                    simulation_params['sim_params']['max_passenger_waiting_time'],
                    simulation_params['network_and_demand']['passenger_schedule_file_name'],
                    simulation_params['passenger_params']['randomize_constants'],
                    simulation_params['passenger_params']['car_to_entrance_walking_time_constant'],
                    simulation_params['passenger_params']['security_check_time_constant'],
                    simulation_params['passenger_params']['waiting_room_to_boarding_gate_walking_time_constant'],
                    simulation_params['passenger_params']['boarding_gate_to_aircraft_time_constant'],
                    simulation_params['passenger_params']['embark_disembark_time_constant'],
                    simulation_params['network_and_demand']['passenger_arrival_process'][
                        'passenger_arrival_distribution']['parameters']['scale'],
                    simulation_params['network_and_demand']['passenger_arrival_process']['num_passengers'],
                    simulation_params['network_and_demand']['aircraft_schedule_file_name'],
                    simulation_params['network_and_demand']['aircraft_arrival_process']['aircraft_arrival_distribution'][
                        'parameters']['scale'],
                    simulation_params['network_and_demand']['aircraft_arrival_process']['num_aircraft'],
                    simulation_params['aircraft_params']['aircraft_model'],
                    simulation_params['aircraft_params']['pax'],
                    simulation_params['aircraft_params']['range'],
                    simulation_params['network_and_demand']['aircraft_arrival_process']['aircraft_fleet_specs'][
                        'jobyS4']['battery_capacity'],
                    simulation_params['aircraft_params']['ground_taxi_speed'],
                    simulation_params['aircraft_params']['time_passenger_embark_disembark'],
                    simulation_params['aircraft_params']['time_pre_charging_processes'],
                    simulation_params['aircraft_params']['time_charging_plug_disconnection'],
                    simulation_params['aircraft_params']['time_post_charging_processes'],
                    simulation_params['aircraft_params']['time_descend_transition'],
                    simulation_params['aircraft_params']['time_hover_descend'],
                    simulation_params['aircraft_params']['time_rotor_spin_down'],
                    simulation_params['aircraft_params']['time_post_landing_safety_checks'],
                    simulation_params['aircraft_params']['time_tug_connection'],
                    simulation_params['aircraft_params']['time_tug_disconnection'],
                    simulation_params['aircraft_params']['time_pre_take_off_check_list'],
                    simulation_params['aircraft_params']['time_rotor_spin_up'],
                    simulation_params['aircraft_params']['time_hover_climb'],
                    simulation_params['aircraft_params']['time_climb_transition'],
                    simulation_params['aircraft_params']['time_charging'],
                    simulation_params['aircraft_params']['charging_time_dist']['distribution_name'],
                    simulation_params['aircraft_params']['charging_time_dist']['parameters']['scale'],
                    performance_metrics['tlof_time'],
                    performance_metrics['average_charge_time'],
                    performance_metrics['average_taxi_time'],
                    performance_metrics['average_aircraft_turnaround_time'],
                    simulation_params['vertiport_params']['layout'],
                    # find_first_int(simulation_params['vertiport_params']['layout']),
                    # find_second_int(simulation_params['vertiport_params']['layout']),
                    performance_metrics['passenger_consolidation_time']['mean'],
                    performance_metrics['passenger_consolidation_time']['max'],
                    performance_metrics['passenger_consolidation_time']['min'],
                    performance_metrics['passenger_waiting_time']['mean'],
                    performance_metrics['passenger_waiting_time']['max'],
                    performance_metrics['passenger_waiting_time']['min'],
                    performance_metrics['passenger_departure_queue_count']['mean'],
                    performance_metrics['passenger_departure_queue_count']['max'],
                    performance_metrics['passenger_departure_queue_count']['min'],
                    performance_metrics['passenger_departure_queue_waiting_times']['mean'],
                    performance_metrics['passenger_departure_queue_waiting_times']['max'],
                    performance_metrics['passenger_departure_queue_waiting_times']['min'],
                    performance_metrics['aircraft_arrival_queue_count']['mean'],
                    performance_metrics['aircraft_arrival_queue_count']['max'],
                    performance_metrics['aircraft_arrival_queue_count']['min'],
                    performance_metrics['aircraft_departure_queue_count']['mean'],
                    performance_metrics['aircraft_departure_queue_count']['max'],
                    performance_metrics['aircraft_departure_queue_count']['min'],
                    performance_metrics['aircraft_holding_times']['mean'],
                    performance_metrics['aircraft_holding_times']['max'],
                    performance_metrics['aircraft_holding_times']['min'],
                    performance_metrics['load_factor']['mean'],
                    performance_metrics['load_factor']['max'],
                    performance_metrics['load_factor']['min'],
                    performance_metrics['aircraft_throughput']['mean'],
                    performance_metrics['aircraft_throughput']['total'],
                    performance_metrics['passenger_throughput']['mean'],
                    performance_metrics['passenger_throughput']['total'],
                    performance_metrics['fato_utilization'],
                    simulation_params['network_and_demand']['passenger_arrival_process']['passenger_interarrival_constant'],
                    simulation_params['network_and_demand']['aircraft_arrival_process']['aircraft_interarrival_constant'],
                    performance_metrics['aircraft_idle_time']['mean'],
                    performance_metrics['aircraft_idle_time']['max'],
                    performance_metrics['aircraft_idle_time']['min'],
                    performance_metrics['passenger_transfer_time']['mean'],
                    performance_metrics['passenger_transfer_time']['max'],
                    performance_metrics['passenger_transfer_time']['min'],
                    performance_metrics['total_simulated_time'])]

        query = '''INSERT INTO performance_metrics 
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);'''
        c.executemany(query, values)

        conn.commit()
        conn.close()



    # trackers = {
    #     'passenger_consolidation_time': passenger_consolidation_time_tracker,
    #     'passenger_waiting_time': passenger_waiting_time_tracker,
    #     'passenger_departure_queue_count': passenger_departure_queue_count_tracker,
    #     'aircraft_arrival_queue_count': aircraft_arrival_queue_count_tracker,
    #     'aircraft_departure_queue_count': aircraft_departure_queue_count_tracker,
    #     'load_factor': load_factor_tracker,
    #     'aircraft_throughput': aircraft_throughput_tracker,
    #     'passenger_throughput': passenger_throughput_tracker,
    #     'fato_utilization': fato_utilization_tracker,
    #     'aircraft_idle_time': aircraft_idle_time_tracker,
    #     'passenger_transfer_time': passenger_transfer_time_tracker
    # }

    # for key, value in trackers.items():
    #     performance_metrics[key]['mean'] = np.mean(value)
    #     performance_metrics[key]['max'] = np.max(value)
    #     performance_metrics[key]['min'] = np.min(value)

    # performance_metrics['aircraft_throughput']['total'] = len(aircraft_departure_queue_tracker)
    # performance_metrics['passenger_throughput']['total'] = len(passenger_departure_queue_tracker)

    # return performance_metrics

# def find_first_int(string):
#     return int(re.findall(r'\d+', string)[0])

# def find_second_int(string):
#     return int(re.findall(r'\d+', string)[1])

