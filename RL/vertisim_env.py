from typing import Any, SupportsFloat, Dict
import gymnasium as gym
import numpy as np
import simpy
from vertisim.vertisim import VertiSim
from vertisim.utils.read_files import read_input_file

class VertiSimEnv(gym.Env):
    def __init__(self, config_file_path):
        super(VertiSimEnv, self).__init__()
        self.config = read_input_file(config_file_path)

        self.action_space = VertiSimEnv.set_action_space(self.config) #TODO: Implement this
        self.observation_space = VertiSimEnv.set_observation_space(self.config) #TODO: Implement this
        self.simpy_env = simpy.Environment()
        self.simulator = VertiSim(self.simpy_env, self.config)

    def step(self, action: Any) -> tuple[Any, SupportsFloat, bool, bool, dict[str, Any]]:
        # Apply action to vertisim and get the next state, reward, terminated, truncated, and info dict
        state, reward, terminated, truncated, info = self.simulator.step(action)
        # # Determine if the episode is done
        # if terminated:
        #     # Reset the environment
        #     self.reset()
        # Return the next state, reward, terminated, truncated, and info dict
        return state, reward, terminated, truncated, info
    
    def reset(self) -> None:
        # Terminate the simulator
        self.simulator.reset()
        # Reset the simulator
        self.simulator = VertiSim(self.simpy_env, self.config)
        return 

    def render(self, mode: str = "human") -> None:
        pass
    
    @staticmethod
    def set_action_space(config):
        raise NotImplementedError
    
    @staticmethod
    def set_observation_space(config):
        raise NotImplementedError