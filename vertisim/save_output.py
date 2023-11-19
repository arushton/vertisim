import sqlite3
import datetime
from collections import defaultdict
from json import dumps
import os

def create_connection(db_file: str):
    try:
        with sqlite3.connect(db_file) as conn:
            return conn
    except sqlite3.Error as e:
        print(e)
        return None
    
def save_output(simulation_params: dict, 
                performance_metrics: defaultdict, 
                simulationID: str, 
                flight_directions: list,
                output_path : str = 'sqlite/db/vertisimDatabase.sqlite') -> str:
    
    # If path doesn't exist, create it
    if not os.path.exists('sqlite/db'):
        os.makedirs('sqlite/db')

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
    metric_names = ['EnergyConsumptionMean', 'EnergyConsumptionMedian', 'EnergyConsumptionStd', 'EnergyConsumptionMax', 'EnergyConsumptionMin', 'EnergyConsumptionTotal', 'FlightDurationMean', 'FlightDurationMedian', 'FlightDurationStd', 'FlightDurationMax', 'FlightDurationMin', 'TripTimeMean', 'TripTimeMedian', 'TripTimeStd', 'TripTimeMax', 'TripTimeMin']

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
            metric_values = [
                energy_metrics['mean'], 
                energy_metrics['median'], 
                energy_metrics['std'],
                energy_metrics['max'], 
                energy_metrics['min'], 
                energy_metrics['total'],
                flight_duration_metrics['mean'], 
                flight_duration_metrics['median'], 
                flight_duration_metrics['std'],
                flight_duration_metrics['max'], 
                flight_duration_metrics['min'],
                trip_time_metrics['mean'],
                trip_time_metrics['median'],
                trip_time_metrics['std'],
                trip_time_metrics['max'],
                trip_time_metrics['min']
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