import mysql.connector
import datetime
from vertisim.utils.helpers import flatten
from collections import defaultdict
from json import dumps

def save_output(simulation_params: dict, 
                performance_metrics: defaultdict, 
                simulationID: str, 
                flight_directions: list, 
                sql_host: str, 
                sql_user: str, 
                sql_pass: str, 
                sql_database: str) -> None:
    
    db = mysql.connector.connect(
        host=sql_host,
        user=sql_user,
        passwd=sql_pass,
        database=sql_database
    )

    cursor = db.cursor()
    
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
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    
    try:
        cursor.execute("""
            INSERT INTO Simulation (SimulationID, Config, Timestamp)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                Timestamp = VALUES(Timestamp), 
                Config = VALUES(Config);
        """, (simulationID, config, timestamp))
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    
    # --- PERFORMANCE METRICS TABLE --- 
    
    metric_names = []
    metric_values = []
    
    for flight_dir in flight_directions:
        metric_names.extend([f'{flight_dir}_ENERGY_CONSUMPTION_MEAN', 
                            f'{flight_dir}_ENERGY_CONSUMPTION_MEDIAN',
                            f'{flight_dir}_ENERGY_CONSUMPTION_STD',
                            f'{flight_dir}_ENERGY_CONSUMPTION_MAX',
                            f'{flight_dir}_ENERGY_CONSUMPTION_MIN',
                            f'{flight_dir}_ENERGY_CONSUMPTION_TOTAL',
                            f'{flight_dir}_FLIGHT_DURATION_MEAN',
                            f'{flight_dir}_FLIGHT_DURATION_MEDIAN',
                            f'{flight_dir}_FLIGHT_DURATION_STD',
                            f'{flight_dir}_FLIGHT_DURATION_MAX',
                            f'{flight_dir}_FLIGHT_DURATION_MIN'])
        
        metrics_for_flight = performance_metrics[flight_dir]
        energy_metrics = metrics_for_flight['energy_consumption']
        flight_duration_metrics = metrics_for_flight['flight_duration']
        
        metric_values.extend([
            energy_metrics['mean'], energy_metrics['median'], energy_metrics['std'],
            energy_metrics['max'], energy_metrics['min'], energy_metrics['total'],
            flight_duration_metrics['mean'], flight_duration_metrics['median'], flight_duration_metrics['std'],
            flight_duration_metrics['max'], flight_duration_metrics['min']
        ])
    
    metric_name_str = ' float, '.join(metric_names) + ' float'
    
    try:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS PerformanceMetrics (
            ID INT AUTO_INCREMENT PRIMARY KEY,
            SimulationID VARCHAR(8),
            {metric_name_str},
            FOREIGN KEY (SimulationID) REFERENCES Simulation(SimulationID));
            """)
    except mysql.connector.Error as err:
        print(f"Error: {err}")

    placeholder = ', '.join(['%s'] * (len(metric_values) + 1))
    
    sql_insert_query = f"""
        INSERT INTO PerformanceMetrics (SimulationID, {', '.join(metric_names)})
        VALUES ({placeholder});
    """

    try:
        cursor.execute(sql_insert_query, [simulationID] + metric_values)
    except mysql.connector.Error as err:
        print(f"Error: {err}")

    db.commit()

    cursor.close()
    db.close()
