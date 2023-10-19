import mysql.connector
import datetime
from utils.helpers import flatten
from collections import defaultdict

def save_output(simulation_params: dict, performance_metrics: defaultdict, simulationID: str) -> None:
    """Saves output to mySQL database.
    Vertisim Database:
    Simulation Table: Config (Primary Key) | Timestamp | SimulationID
    Performance Metrics Table: ID (Primary Key) | SimulationID | Metric_1 | Metric_2 | ... | Metric_N """
    
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="*()&*!@&*382",
        database="vertisimdatabase"
    )

    cursor = db.cursor()
    
    # --- SIMULATION TABLE ---
    
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    config = flatten(simulation_params)
    
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS Simulation (
                            Config TEXT PRIMARY KEY,
                            Timestamp DATETIME,
                            SimulationID TEXT 
                        ); """)
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    
    try:
        cursor.execute("""INSERT INTO Simulation (Config, Timestamp, SimulationID)
                        VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE Timestamp = VALUES(Timestamp), SimulationID = VALUES(SimulationID);""", 
                        (config, timestamp, simulationID))
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    
    # --- PERFORMANCE METRICS TABLE --- 
    
    # Metrics: Energy Consumption, Flight Time
    
    
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS PerformanceMetrics (
                            ID INT AUTO_INCREMENT PRIMARY KEY,
                            SimulationID TEXT,
                            Metric_1 FLOAT,
                            Metric_2 FLOAT,
                            ...,
                            Metric_N FLOAT,
                            FOREIGN KEY (SimulationID) REFERENCES Simulation(SimulationID) 
                        );""")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    
    try:
        cursor.execute("""
            INSERT INTO PerformanceMetrics (SimulationID, Metric_1, Metric_2, ..., Metric_N)
            VALUES (%s, %s, %s, ..., %s);
        """, (simulationID, *performance_metrics))
    except mysql.connector.Error as err:
        print(f"Error: {err}")

    # Commit the changes
    db.commit()
    
    # Close the cursor and disconnect from the database
    cursor.close()
    db.close()
    