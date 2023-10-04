import simpy
from typing import Any, Dict
from sim_setup import SimSetup
from sim_engine_runner import SimEngineRunner
import time
from utils.read_files import read_input_file
from run_step_by_step_simulation import run_step_by_step_simulation


class VertiSim:
    def __init__(self, 
                 env: simpy.Environment, 
                 config: Dict, 
                 terminal_event: simpy.Event = None, 
                 stopping_events: Dict = None,
                 reward_function_parameters: Dict = None):
        # sourcery skip: raise-specific-error
        self.env = env
        self.terminal_event = terminal_event
        self.config = config

        self.sim_start_time = time.time()
        self.sim_setup = SimSetup(env=self.env,
                                  sim_params=config['sim_params'],
                                  network_and_demand_params=config['network_and_demand_params'],
                                  airspace_params=config['airspace_params'],
                                  passenger_params=config['passenger_params'],
                                  aircraft_params=config['aircraft_params'],
                                  output_params=config['output_params'],
                                  stopping_events=stopping_events)

        self.sim_engine_runner = SimEngineRunner(env=self.env,
                                                 sim_setup=self.sim_setup,
                                                 stopping_events=stopping_events,
                                                 reward_function_parameters=reward_function_parameters)

    def run_one_step(self, action):
        # Pass action to the SimEngineRunner
        self.sim_engine_runner.apply_action(action)
        # Run the simulator for one timestep
        state, reward, terminated, truncated = self.sim_engine_runner.advance_to_next_stopping_event()
        # Return new state, reward, and terminated and truncated flag to the VertiSimEnv
        return state, reward, terminated, truncated
    
    def reset_simulation(self):
        # Get the initial states of the simulation using the config file.
        return self.sim_engine_runner.get_initial_state()

    def render(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError
    
    def run_uninterrupted_simulation(self, flight_schedule_file_path):
        """
        Run the simulation until the terminal event is triggered.
        """
        self.sim_engine_runner.run_uninterrupted_simulation(flight_schedule_file_path=flight_schedule_file_path)

    def print_total_time_to_run(self):
        end_time = time.time()
        time_taken = end_time - self.sim_start_time
        print(f'Simulation Completed. Total time to run: {round(time_taken, 2)} seconds')  

    def run(self):
        if not self.sim_setup.sim_params['step_by_step_sim']:
            self.run_uninterrupted_simulation(flight_schedule_file_path=self.sim_setup.network_and_demand_params['flight_schedule_file_path'])
        elif self.sim_setup['step_by_step_sim'] == 'hil':
            run_step_by_step_simulation(env=self.env,
                                        vertiports=self.sim_setup.vertiports,
                                        airspace=self.sim_setup.airspace,
                                        structural_entity_groups=self.sim_setup.structural_entity_groups,
                                        system_manager=self.sim_setup.system_manager,
                                        max_sim_time=self.sim_setup.sim_params['max_sim_time'],
                                        simulation_states=self.sim_setup.sim_params['simulation_states'])
        elif self.sim_setup['step_by_step_sim'] != 'auto':
            raise Exception(f"Step-by-step simulation is only supported for hil and autoresponse types. Received {self.sim_setup['step_by_step_sim']} instead.")

        self.print_total_time_to_run()
        performance_metrics = self.sim_setup.calculate_performance_metrics()
        self.sim_setup.save_results(performance_metrics)