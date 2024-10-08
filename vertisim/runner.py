import argparse
from multiprocessing import Pool, Process, Manager
from queue import Empty
from .vertisim import VertiSim
import json
import simpy
import sqlite3
from collections import defaultdict
from .utils.helpers import read_config_file
import argparse
import glob
import os
from queue import Empty
import time

# Constants for database
QUEUE_TIMEOUT = 5  # Timeout in seconds for reading from queue

def parse_args():
    parser = argparse.ArgumentParser(description='Run VertiSim with a configuration file')
    parser.add_argument('-ec', '--env_config', type=str, help='Path to the config.json file')
    parser.add_argument('-br', '--batch_run', action='store_true', help='Run the simulation in batch')
    parser.add_argument('-nc', '--n_cores', type=int, help='Number of cores to run the simulation on', default=1)
    parser.add_argument('-paxp', '--passenger_schedule_folder', type=str, help='Path to the passenger schedule file', default=None)
    return parser.parse_args()

def runner(config, queue, passenger_schedule_file_path=None):
    config['network_and_demand_params']['passenger_schedule_file_path'] = passenger_schedule_file_path
    env = simpy.Environment()
    vertisim = VertiSim(env=env, config=config)
    results = vertisim.run()

    if results:
        queue.put(results)

def run_simulation_with_config(config_path, base_config):
    config = base_config.copy()
    config['network_and_demand_params']['passenger_schedule_file_path'] = config_path
    config['sim_params']['logging'] = False
    print(f"Running simulation with config: {config_path}")
    runner(config)

def db_writer(queue, db_file):
    """Process that writes data to the SQLite database from the queue."""
    conn = create_connection(db_file)
    cursor = conn.cursor()

    while True:
        try:
            # Get data from the queue
            data = queue.get(timeout=QUEUE_TIMEOUT)
        except Empty:
            continue  # Continue if no data is available in the queue
        if data is None:
            break  # Exit if sentinel value is received

        # Unpack the result dictionary from the queue
        try:
            save_results_to_db(cursor, data)
            conn.commit()
        except sqlite3.Error as err:
            print(f"Error writing to database: {err}")

    conn.close()
    print("Database writer process has shut down.")

def create_connection(db_file: str, timeout: int = 30):
    """Create a database connection to the SQLite database specified by db_file with the specified timeout."""
    try:
        conn = sqlite3.connect(db_file, timeout=timeout)
        conn.execute("PRAGMA journal_mode=WAL;")  # Enable Write-Ahead Logging for better concurrency
        return conn
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return None
    
def save_results_to_db(cursor, results):
    """Helper function to save results to the database."""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Simulation (
                SimulationID VARCHAR(8) PRIMARY KEY,
                SimulatedDate TEXT,
                Algorithm TEXT,
                NumAircraft INTEGER,
                NSpilled INTEGER,
                NFlights INTEGER,
                NumPax INTEGER
            );
        """)
        # Insert or update the simulation results in the database
        cursor.execute("""
            INSERT INTO Simulation (SimulationID, SimulatedDate, Algorithm, NumAircraft, NSpilled, NFlights, NumPax)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(SimulationID) DO UPDATE SET
            SimulatedDate=excluded.SimulatedDate,
            Algorithm=excluded.Algorithm,
            NumAircraft=excluded.NumAircraft,
            NSpilled=excluded.NSpilled,
            NFlights=excluded.NFlights,
            NumPax=excluded.NumPax;
        """, (
            results['SimulationID'],
            results['SimulatedDate'],
            results['Algorithm'],
            results['NumAircraft'],
            results['NSpilled'],
            results['NFlights'],
            results['NumPax']
        ))
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

if __name__ == '__main__':
    start_time = time.time()  # Start time of the code execution
    args = parse_args()

    if args.env_config:
        env_config = read_config_file(args.env_config)
        env_config['sim_params']['algorithm'] = "VertiSimHeuristics"
    else:
        raise ValueError("Please provide a configuration file")

    print(f"Running VertiSimHeuristics")

    # Create a Manager for the queue
    manager = Manager()
    queue = manager.Queue()

    # Start the database writer process
    db_file = f"{env_config['output_params']['performance_metrics_db_name']}.sqlite"
    db_process = Process(target=db_writer, args=(queue, db_file))
    db_process.start()

    if args.batch_run:
        passenger_schedule_folder = args.passenger_schedule_folder
        csv_files = glob.glob(os.path.join(passenger_schedule_folder, "*.csv"))

        if len(csv_files) == 0:
            raise ValueError(f"No CSV files found in folder: {passenger_schedule_folder}")

        print(f"Running simulations in batch mode on {args.n_cores} cores")
        
        # Create a pool of workers and run the simulations in parallel
        with Pool(processes=args.n_cores) as pool:
            pool.starmap(runner, [(env_config, queue, passenger_schedule_file_path) for passenger_schedule_file_path in csv_files])
    else:
        runner(env_config, queue)

    # Signal the database writer process to shut down
    queue.put(None)
    db_process.join()
    print("All simulations completed, and database writer has shut down.")

    end_time = time.time()  # End time of the code execution
    run_time = end_time - start_time  # Calculate the code run time
    print(f"Code run time: {round(run_time/60, 1)} minutes")
