import argparse
from multiprocessing import Pool
from .vertisim import VertiSim
import json
import simpy
from .utils.helpers import read_config_file
import glob
import os

def parse_args():
    parser = argparse.ArgumentParser(description='Run VertiSim with a configuration file')
    parser.add_argument('-ec', '--env_config', type=str, help='Path to the config.json file')
    parser.add_argument('-br', '--batch_run', action='store_true', help='Run the simulation in batch')
    parser.add_argument('-nc', '--n_cores', type=int, help='Number of cores to run the simulation on', default=1)
    return parser.parse_args()

def runner(config):
    env = simpy.Environment()
    vertisim = VertiSim(env=env, config=config)
    vertisim.run()

def run_simulation_with_config(config_path, base_config):
    config = base_config.copy()
    config['network_and_demand_params']['passenger_schedule_file_path'] = config_path
    config['sim_params']['logging'] = False
    print(f"Running simulation with config: {config_path}")
    runner(config)

if __name__ == '__main__':
    args = parse_args()

    if args.env_config:
        env_config = read_config_file(args.env_config)
        env_config['sim_params']['algorithm'] = "VertiSimHeuristics"
    else:
        raise ValueError("Please provide a configuration file")

    print(f"Running VertiSimHeuristics")

    if args.batch_run:
        passenger_schedule_folder = "vertisim/vertisim/input/passenger/spill_demand/1_hub_8_spoke"
        csv_files = glob.glob(os.path.join(passenger_schedule_folder, "*.csv"))

        print(f"Running simulations in batch mode on {args.n_cores} cores")
        
        # Create a pool of workers and run the simulations in parallel
        with Pool(processes=args.n_cores) as pool:
            pool.starmap(run_simulation_with_config, [(csv_file, env_config) for csv_file in csv_files])
    else:
        runner(env_config)
