import json
import time
from sim_setup import SimSetup
import os

def main(config):
    start_time = time.time()

    SimSetup(sim_params=config['sim_params'],
             network_and_demand=config['network_and_demand'],
             vertiport_params=config['vertiport_params'],
             passenger_params=config['passenger_params'],
             aircraft_params=config['aircraft_params'],
             output_params=config['output_params'],
             sim_start_time=start_time
             )

if __name__ == "__main__":
    cwd = os.getcwd()
    with open(os.path.join(cwd, 'config.json'), 'r') as config_file:
        config = json.load(config_file)
        
    main(config)
