from typing import Any, SupportsFloat, Dict
import gymnasium as gym
import numpy as np
import simpy
from vertisim.vertisim import VertiSim
from vertisim.utils.read_files import read_input_file

class VertiSimEnv(gym.Env):
    def __init__(self, config_file_path: str):
        super(VertiSimEnv, self).__init__()
        self.config = read_input_file(file_path=config_file_path)

        self.action_space = VertiSimEnv.set_action_space(self.config) #TODO: Implement this
        self.observation_space = VertiSimEnv.set_observation_space(self.config) #TODO: Implement this
        self.simpy_env = simpy.Environment()
        self.stopping_events = self.define_stopping_events()
        self.terminal_event = self.simpy_env.event()
        self.simulator = VertiSim(env=self.simpy_env, 
                                  config=self.config, 
                                  terminal_event=self.terminal_event, 
                                  stopping_events=self.stopping_events)

    def step(self, action: Any) -> tuple[Any, SupportsFloat, bool, bool, dict[str, Any]]:
        # Apply action to vertisim and get the next state, reward, terminated, truncated, and info dict
        state, reward, terminated, truncated, info = self.simulator.run_one_step(action)
        return state, reward, terminated, truncated, info
    
    def reset(self) -> None:
        # Terminate the simulation
        self.terminal_event.succeed()
        # Recreate the terminal event
        self.terminal_event = self.simpy_env.event()
        # Reset the simulator and return the initial state
        self.simulator = VertiSim(self.simpy_env, self.config, self.terminal_event)
        return self.simulator.reset_simulation()

    def render(self, mode: str = "human") -> None:
        pass

    def define_stopping_events(self):
        return {
            'passenger_arrival_event': self.simpy_env.event(),
            'aircraft_faf_arrival_event': self.simpy_env.event(),
            'aircraft_parking_pad_arrival_event': self.simpy_env.event(),
            'aircraft_departure_fix_departure_event': self.simpy_env.event(),
            'charging_start_event': self.simpy_env.event(),
            'charging_end_event': self.simpy_env.event()
        }    
    
    @staticmethod
    def set_action_space(config):
        raise NotImplementedError
    
    @staticmethod
    def set_observation_space(config):
        raise NotImplementedError
