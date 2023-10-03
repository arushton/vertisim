import simpy
from typing import Any, Dict
from sim_setup import SimSetup
from vertisim.sim_engine_runner import SimEngineRunner
import time
from utils.read_files import read_input_file
from test_config import sim_params, network_and_demand_params, airspace_params, passenger_params, aircraft_params, output_params


class VertiSim:
    def __init__(self, env: simpy.Environment, config, terminal_event: simpy.Event):
        self.env = env
        self.terminal_event = env.event()
        self.config = config

        start_time = time.time()
        self.sim_setup = SimSetup(env=self.env,
                                  sim_params=sim_params,
                                  network_and_demand_params=network_and_demand_params,
                                  airspace_params=airspace_params,
                                  passenger_params=passenger_params,
                                  aircraft_params=aircraft_params,
                                  output_params=output_params)

        self.sim_engine_runner = SimEngineRunner(env=env)

        # TODO: Start vertisim and run step-by-step simulation. Get the states and continue the simulation until the terminal event is triggered.

    def run_one_step(self, action):
        # Pass action to the SimEngineRunner
        self.sim_engine_runner.apply_action(action)
        # Run the simulator for one timestep
        state, reward, terminated, truncated = self.sim_engine_runner.run_one_timestep()
        # Return new state, reward, and terminated and truncated flag to the VertiSimEnv
        return state, reward, terminated, truncated
    
    def reset_simulation(self):
        # Get the initial states of the simulation using the config file.
        return self.sim_engine_runner.get_initial_state()

    def render(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError