import simpy
from typing import Any, Dict
from sim_setup import SimSetup
import time
from utils.read_files import read_input_file


class VertiSim:
    def __init__(self, env: simpy.Environment, config_file_path: str):
        self.env = env
        self.terminal_event = env.event()
        config = read_input_file(config_file_path)

        start_time = time.time()


        # TODO: Start vertisim and run step-by-step simulation. Get the states and continue the simulation until the terminal event is triggered.

    def step(self):
        # TODO: Implement this
        state: Dict[str, Any] = {}
        reward: float = 0.0
        terminated: bool = False
        truncated: bool = False
        info: Dict[str, Any] = {}
        return state, reward, terminated, truncated, info
    
    def reset(self):
        # Trigger the terminal event
        self.terminal_event.succeed()
        # Restart the simulation
        self.simulator = VertiSim(self.env, self.config)
        # Return the initial state
        return self.simulator.get_initial_state()

    def render(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError