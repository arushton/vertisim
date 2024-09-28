import sqlite3
import datetime
from collections import defaultdict
from json import dumps
import json
from typing import Dict, List
import pandas as pd
import os
import re
from .utils.json_formatter import create_trajectory_json
from .utils.helpers import get_str_before_first_occurrence_of_char

def create_connection(db_file: str):
    try:
        with sqlite3.connect(db_file) as conn:
            return conn
    except sqlite3.Error as e:
        print(e)
        return None
    
def save_output(simulation_params: dict, 
                trajectories: dict,
                performance_metrics: defaultdict, 
                simulationID: str, 
                flight_directions: list) -> str:

    # Save trajectories
    if simulation_params['sim_params']['save_trajectories']:
        save_trajectories(trajectories=trajectories,
                          simulation_params=simulation_params,
                          output_dir=simulation_params['output_params']['output_folder_path'])     

    # Extract simulated date from filename
    simulated_date = extract_date_from_filename(filename=simulation_params['network_and_demand_params']['passenger_schedule_file_path']) 
    # Get the number of aircraft
    num_aircraft = get_num_aircraft(network_and_demand_params=simulation_params['network_and_demand_params'])          
    
    # Save performance metrics
    save_performance_metrics(simulation_params=simulation_params,
                                performance_metrics=performance_metrics,
                                simulationID=simulationID,
                                flight_directions=flight_directions,
                                simulated_date=simulated_date,
                                algorithm=simulation_params['sim_params']['algorithm'],
                                num_aircraft=num_aircraft, 
                                performance_metrics_db_name=simulation_params['output_params']['performance_metrics_db_name'])
    
def extract_date_from_filename(filename: str) -> str:
    if not filename:
        return None
    # Define a regex pattern that matches digits with an underscore, such as '5_23'
    pattern = r'(\d+_\d+)'
    
    # Search for the pattern in the filename
    match = re.search(pattern, filename)
    
    # If a match is found, return the first match group
    if match:
        return match.group(1)
    else:
        return None

def get_num_aircraft(network_and_demand_params: dict) -> int:
    return sum(
        vertiport['aircraft_arrival_process']['num_initial_aircraft_at_vertiport']
        for _, vertiport in network_and_demand_params['vertiports'].items()
    )

def save_performance_metrics(simulation_params: dict,
                             performance_metrics: defaultdict,
                             simulationID: str,
                             flight_directions: list,
                             simulated_date: str,
                             algorithm: str,
                             num_aircraft: int,
                             performance_metrics_db_name: str) -> str:

    output_path = f"{simulation_params['output_params']['output_folder_path']}/sqlite/{performance_metrics_db_name}.sqlite"
    print(f"Saving performance metrics to {output_path}\n")
    # If path doesn't exist, create it
    if not os.path.exists(f"{simulation_params['output_params']['output_folder_path']}/sqlite"):
        os.makedirs(f"{simulation_params['output_params']['output_folder_path']}/sqlite", exist_ok=True)

    conn = create_connection(output_path)
    assert conn, 'Could not establish database connection.'
    cursor = conn.cursor()
    
    # --- SIMULATION TABLE ---
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    config = dumps(simulation_params)
        
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Simulation (
                SimulationID VARCHAR(8) PRIMARY KEY,
                Config TEXT,
                Timestamp DATETIME
            );
        """)
        
        cursor.execute("SELECT SimulationID FROM Simulation WHERE SimulationID = ?", (simulationID,))
        data=cursor.fetchone()
        if data is None:
            cursor.execute("INSERT INTO Simulation (SimulationID, Config, Timestamp) VALUES (?, ?, ?)", (simulationID, config, timestamp))
        else:
            cursor.execute("UPDATE Simulation SET Timestamp = ?, Config = ? WHERE SimulationID = ?", (timestamp, config, simulationID))
            
    except sqlite3.Error as err:
        print(f"Error: {err}")
    
    # --- PERFORMANCE METRICS TABLE --- 
    metric_names = ['SimulatedDate',
                    'Algorithm',
                    'NumAircraft',
                    'EnergyConsumptionMean', 
                    'EnergyConsumptionStd', 
                    'EnergyConsumptionTotal', 
                    'FlightDurationMean', 
                    'FlightDurationMedian', 
                    'FlightDurationStd', 
                    'FlightDurationMax', 
                    'FlightDurationMin',
                    'WaitingTimeMean', 
                    'WaitingTimeMedian',
                    'WaitingTimeStd', 
                    'WaitingTimeMax', 
                    'WaitingTimeMin', 
                    'TripTimeMean', 
                    'TripTimeMedian', 
                    'TripTimeStd', 
                    'TripTimeMax', 
                    'TripTimeMin', 
                    'NSpilled', 
                    'NFlights', 
                    'MeanReward', 
                    'TotalReward']

    try:
        # Create the table with dynamic columns
        columns = ', '.join([f"{metric} FLOAT" for metric in metric_names])
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS PerformanceMetrics (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            SimulationID VARCHAR(8),
            FlightDirection TEXT,
            {columns},
            FOREIGN KEY (SimulationID) REFERENCES Simulation(SimulationID));
        """)
    except sqlite3.Error as err:
        print(f"Error: {err}")
        
    try:
        for flight_dir in flight_directions:
            metrics_for_flight = performance_metrics[flight_dir]
            energy_metrics = metrics_for_flight['energy_consumption']
            flight_duration_metrics = metrics_for_flight['flight_duration']
            trip_time_metrics = metrics_for_flight['passenger_trip_time']
            n_spilled = metrics_for_flight['n_spilled']
            n_flights = metrics_for_flight['n_flights']
            # Flight direction is in the format 'origin_destination'. Split it into two separate columns
            origin, _ = flight_dir.split('_')
            waiting_time_metrics = performance_metrics[origin]['passenger_waiting_time']
            mean_reward = metrics_for_flight['mean_reward']
            total_reward = metrics_for_flight['total_reward']
            metric_values = [
                simulated_date,
                algorithm,
                num_aircraft,
                energy_metrics['mean'], 
                energy_metrics['std'],
                energy_metrics['total'],
                flight_duration_metrics['mean'], 
                flight_duration_metrics['median'],
                flight_duration_metrics['std'],
                flight_duration_metrics['max'],
                flight_duration_metrics['min'],
                waiting_time_metrics['mean'],
                waiting_time_metrics['median'],
                waiting_time_metrics['std'],
                waiting_time_metrics['max'],
                waiting_time_metrics['min'],                
                trip_time_metrics['mean'],
                trip_time_metrics['median'],
                trip_time_metrics['std'],
                trip_time_metrics['max'],
                trip_time_metrics['min'],
                n_spilled,
                n_flights,
                mean_reward,
                total_reward
            ]
    
            placeholder = ', '.join(['?'] * (len(metric_values) + 2))
            sql_insert_query = f"INSERT INTO PerformanceMetrics (SimulationID, FlightDirection, {', '.join(metric_names)}) VALUES ({placeholder});"
            cursor.execute(sql_insert_query, [simulationID, flight_dir] + metric_values)
            
    except sqlite3.Error as err:
        print(f"Error: {err}")

    conn.commit()
    cursor.close()
    conn.close()
    
    return os.getcwd() + output_path


def save_trajectories(trajectories: Dict,
                      simulation_params: Dict,
                      output_dir: str) -> None:
    # Save agent trajectories
    for key, value in trajectories.items():
        df = convert_dict_to_dataframe(dic=value, orient='index')
        trajectory_output_file_name = get_output_filename(output_dir=output_dir, file_name=key)
        save_df_to_csv(df=df, output_file_name=trajectory_output_file_name)

        # Convert trajectory df to geoJSON and save
        agent_type = get_str_before_first_occurrence_of_char(key, '_')
        if json_trajectory := create_trajectory_json(
                df=df, agent_type=agent_type,
                only_aircraft_simulation=simulation_params['sim_params']['only_aircraft_simulation']
        ):
            with open(trajectory_output_file_name + '.geojson', 'w') as f:
                json.dump(json_trajectory, f)

def convert_dict_to_dataframe(dic: Dict, orient: str = 'columns') -> pd.DataFrame:
    df = pd.DataFrame.from_dict(dic, orient=orient)
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'time'}, inplace=True)
    return df

def get_output_filename(output_dir: str, file_name: str) -> str:
    return os.path.join(output_dir, file_name)

def save_df_to_csv(df: pd.DataFrame, output_file_name: str) -> None:
    df.to_csv(f'{output_file_name}.csv')