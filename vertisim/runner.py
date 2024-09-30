import argparse
from .vertisim import VertiSim
import json
import simpy
from .utils.helpers import read_config_file
import glob
import os

def parse_args():
    parser = argparse.ArgumentParser(description='Run VertiSim with a configuration file')
    parser.add_argument('-ec', '--env_config', type=str, help='Path to the config.json file')
    parser.add_argument('-sr', '--serial_run', action='store_true', help='Run the simulation in serial')
    parser.add_argument("--num_runs", "-nr", type=int, help="The number of runs to execute", default=1)
    return parser.parse_args()

def runner(config):

    env = simpy.Environment()
    
    vertisim = VertiSim(env=env, 
                        config=config)
    vertisim.run()

if __name__ == '__main__':
    args = parse_args()

    if args.env_config:
        env_config = read_config_file(args.env_config)
        env_config['sim_params']['algorithm'] = "VertiSimHeuristics"

        print(f"Running VertiSimHeuristics for {args.num_runs} runs")

        if args.serial_run:
            passenger_schedule_folder = "vertisim/vertisim/input/passenger/spill_demand/test"
            csv_files = glob.glob(os.path.join(passenger_schedule_folder, "*.csv"))

            for csv_file in csv_files:
                print(f"Running simulation for: {csv_file}")

                env_config['network_and_demand_params']['passenger_schedule_file_path'] = csv_file
                env_config['sim_params']['logging'] = False

                if args.num_runs:
                    for i in range(args.num_runs):
                        runner(env_config)
                else:
                    runner(env_config)
        else:
            runner(env_config)