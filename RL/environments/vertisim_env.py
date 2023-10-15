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

        self.action_space = VertiSimEnv.set_action_space(self.config)
        self.observation_space = VertiSimEnv.set_observation_space(self.config)
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
        return gym.spaces.Discrete(config['sim_params']['num_actions'])
    
    @staticmethod
    def set_observation_space(config):
        # Vertiport states
        # Get the number of vertiports
        num_vertiports = len(config['network_and_demand_params']['vertiports'])

        # Get number of aircraft defined in the config file
        num_aircraft = sum(
            vertiport['aircraft_arrival_process']['num_initial_aircraft_in_vertiport']
            for vertiport in config['network_and_demand_params']['vertiports'].items()
        )

        # Get the total number of state variables
        total_state_variables = num_vertiports * config['sim_params']['num_vertiport_state_variables'] +\
                                num_aircraft * config['sim_params']['num_aircraft_state_variables'] +\
                                num_vertiports * config['sim_params']['num_environmental_state_variables']
        
        # Return the observation space
        return gym.spaces.Box(low=0, high=np.inf, shape=(total_state_variables,), dtype=np.float32)



