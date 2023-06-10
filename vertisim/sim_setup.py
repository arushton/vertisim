import time

# from utils.defaults import sim_params, network_and_demand, vertiport_params, aircraft_params, output_params
import simpy
from typing import Dict, List
import pandas as pd
from collections import defaultdict
from aircraft.aircraft_arrival_setup import AircraftArrivalSetup
from event_saver import EventSaver
from vertiport_manager import VertiportManager
from module_setup import vertiport_config, create_vertiport_layouts, set_taxi_operations_config, create_airspace_layout
from passenger_arrival_setup import PassengerArrivalSetup
from performance_metrics import PerformanceMetrics
from save_output import save_output
from scheduler import Scheduler
from logger import Logger
from run_step_by_step_simulation import run_step_by_step_simulation
from utils.create_output_folders import create_output_folders
from utils.bundle_passenger_related_distributions import bundle_distributions
from utils.calc_vertiport_distances_from_lat_lng import calc_vertiport_distances
from utils.helpers import set_seed, get_random_id, get_all_aircraft_models, create_dict_for_fixes, check_not_none
from utils.import_aircraft_energy_consumption_data import import_aircraft_energy_consumption_data
from utils.setup_distributions import setup_passenger_distributions
from utils.units import sec_to_ms



class SimSetup:
    def __init__(self,
                 sim_params,
                 network_and_demand: Dict,
                 airspace_params: Dict,
                 passenger_params: Dict,
                 aircraft_params: Dict,
                 output_params: Dict,
                 sim_start_time: int):
        self.sim_params = sim_params
        self.network_and_demand = network_and_demand
        self.airspace_params = airspace_params
        self.passenger_params = passenger_params
        self.aircraft_params = aircraft_params
        self.output_params = output_params
        self.sim_start_time = sim_start_time

        self.sim_start_timestamp = sec_to_ms(1625065200)  # Wednesday, June 30, 2021 8:00:00 AM PT
        set_seed(sim_params['random_seed'])
        self.env = self.create_environment()
        self.output_folder_path = create_output_folders(self.output_params['output_folder_path'])
        self.logger, self.aircraft_logger, self.passenger_logger = self.create_loggers()
        self.vertiport_layouts = self.create_vertiport_layout()
        self.vertiport_ids = self.get_vertiport_ids() # List of vertiport ids        
        self.vertiport_distances = self.compute_vertiport_distances() # pd.DataFrame of vertiport connectivity, locations and distances
        self.check_inputs()
        self.num_destinations = self.get_num_destinations()
        self.vertiports = self.create_vertiports() # Dictionary of vertiport entities
        self.airspace = self.create_airspace()      
        self.node_locations = self.build_node_locations_dict()
        self.structural_entity_groups = self.merge_structural_entity_groups()
        self.event_saver = self.create_event_saver()
        self.taxi_config = self.set_taxi_operations_config()
        self.aircraft_energy_consumption_data = self.set_aircraft_energy_consumption_data() # Dictionary of aircraft energy consumption data
        self.passenger_distributions = self.create_passenger_distributions()

        if self.network_and_demand['flight_schedule_file_name'] is not None:
            self.fixed_schedule = True
        else:
            self.fixed_schedule = False

        self.scheduler = self.create_scheduler()
        self.vertiport_manager = self.create_vertiport_manager()

        self.create_aircraft_arrival_process()
        self.create_passenger_arrival_process()
        self.run_simulation()

        self.sim_id = get_random_id()
        self.performance_metrics = self.calculate_performance_metrics()
        self.save_results()

    def create_environment(self):
        """
        Creates the environment
        """
        return simpy.Environment()   

    def create_loggers(self):
        """
        Sets the loggers
        """
        logger = Logger(output_folder_path=self.output_folder_path)
        logger.create_logger(name='main', env=self.env)

        aircraft_logger = Logger(output_folder_path=self.output_folder_path)
        aircraft_logger.create_logger(name='aircraft', env=self.env)

        passenger_logger = Logger(output_folder_path=self.output_folder_path)
        passenger_logger.create_logger(name='passenger', env=self.env)

        return logger, aircraft_logger, passenger_logger

    def create_vertiport_layout(self):
        """
        Creates the vertiport layouts and adds them to the network_and_demand dictionary
        """
        # Create vertiport layouts
        vertiport_layouts = create_vertiport_layouts(network_and_demand=self.network_and_demand,
                                                     output_folder_path=self.output_folder_path)
        if self.sim_params['verbose']:
            print("Success: Vertiport layout(s) created.")
        return vertiport_layouts
    
    def get_vertiport_ids(self) -> List:
        """
        Returns the vertiport ids
        """
        return list(self.network_and_demand['vertiports'].keys())    
    
    def compute_vertiport_distances(self) -> pd.DataFrame:
        """
        Imports the vertiport distance
        """
        # Import vertiport distance
        vertiport_distances = calc_vertiport_distances(
            vertiport_network_file_path=self.network_and_demand['vertiport_network_file_path'],
            vertiport_ids=self.vertiport_ids,
            vertiport_layouts=self.vertiport_layouts,
            network_simulation=self.sim_params['network_simulation'])
        if self.sim_params['verbose']:
            print("Success: Vertiport network imported.")
        return vertiport_distances

    def check_inputs(self):
        """
        Checks the inputs
        """
        if len(self.vertiport_ids) != len(self.vertiport_layouts.keys()):
            raise ValueError('The number of vertiport ids and layouts do not match. Check the vertiport network or vertiport input configs.')

    def get_num_destinations(self) -> int:
        """
        Returns the number of destinations
        """
        return len(self.vertiport_distances)

    def create_vertiports(self) -> Dict:
        # Set vertiport configurations
        return vertiport_config(
            env=self.env,
            vertiport_layouts=self.vertiport_layouts,
            vertiports=self.network_and_demand['vertiports'],
            vertiport_ids=self.vertiport_ids
        )
    
    def create_event_saver(self):
        """
        Creates the event saver
        """
        # Create event saver
        return EventSaver(env=self.env, 
                          vertiports=self.vertiports, 
                          sim_start_timestamp=self.sim_start_timestamp, 
                          sim_params=self.sim_params,
                          node_locations=self.node_locations)    

    def set_taxi_operations_config(self):
        """
        Sets the taxi operations configuration
        """
        # Set taxi operations config
        taxi_config = set_taxi_operations_config(
            is_simultaneous_taxi_and_take_off_allowed=self.sim_params['simultaneous_taxi_and_take_off']
        )
        if self.sim_params['verbose']:
            print("Success: Vertiport configuration is set.")
        return taxi_config

    def set_aircraft_energy_consumption_data(self):
        """
        Sets the aircraft energy consumption data
        """
        if self.sim_params['battery_model_sim']:
            return self.import_aircraft_energy_consumption_data()
        else:
            return None

    def import_aircraft_energy_consumption_data(self):
        """
        Imports the aircraft energy consumption data
        """
        # Import aircraft energy consumption data
        if self.aircraft_params['aircraft_energy_consumption_data_folder_path'] is not None:
            aircraft_energy_consumption_data = import_aircraft_energy_consumption_data(
                folder_path=self.aircraft_params['aircraft_energy_consumption_data_folder_path'],
                aircraft_models=get_all_aircraft_models(self.network_and_demand),
                ranges=list(self.vertiport_distances['distance']))
            if self.sim_params['verbose']:
                print("Success: Aircraft energy consumption data imported.")
        else:
            if self.sim_params['verbose']:
                print("Aircraft energy consumption data folder path is not provided.")
            aircraft_energy_consumption_data = None
        return aircraft_energy_consumption_data

    def bundle_passenger_distributions(self):
        # Bundle passenger related distributions
        return bundle_distributions(
            self.passenger_params['car_to_entrance_walking_time_dist'],
            self.passenger_params['security_check_time_dist'],
            self.passenger_params['waiting_room_to_boarding_gate_walking_time_dist'],
            self.passenger_params['boarding_gate_to_aircraft_time_dist'],
            self.passenger_params['embark_disembark_time_dist'],
            self.passenger_params['deboard_aircraft_and_walk_to_exit_dist'],
        )

    def create_passenger_distributions(self):
        """
        Creates the passenger distribution
        """
        if self.sim_params['only_aircraft_simulation']:
            return None
        passenger_distributions_bundle = self.bundle_passenger_distributions()
        # Setup passenger distributions
        return setup_passenger_distributions(**passenger_distributions_bundle)

    def create_scheduler(self):
        # Create scheduler
        return Scheduler(env=self.env,
                            vertiports=self.vertiports,
                            vertiport_manager=None,
                            aircraft_capacity=self.aircraft_params['pax'],
                            is_fixed_schedule=self.fixed_schedule,
                            logger=self.logger,
                            aircraft_logger=self.aircraft_logger,
                            passenger_logger=self.passenger_logger)

    def create_airspace(self):
        # Create airspace
        return create_airspace_layout(env=self.env,
                                    vertiports=self.vertiports,
                                    vertiport_distances=self.vertiport_distances,
                                    airspace_params=self.airspace_params)
    
    def build_node_locations_dict(self):
        # Build node locations dictionary
        node_locations = {}
        # Merge all vertiport element locations
        for _, vertiport_config in self.vertiports.items():
            node_locations |= vertiport_config.vertiport_layout.vertiport_element_locations
        # Merge all airspace element locations
        node_locations |= self.airspace.waypoint_locations
        node_locations |= {None: None}
        return node_locations
    
    def merge_structural_entity_groups(self) -> dict:
        merged_dict = defaultdict(list)
        for _, vertiport_config in self.vertiports.items():
            structural_entity_groups = vertiport_config.vertiport_layout.structural_entity_groups
            for entity, value in structural_entity_groups.items():
                merged_dict[entity].extend(value)
        fix_nodes = create_dict_for_fixes(self.airspace.waypoint_ids)
        merged_dict |= fix_nodes
        return dict(merged_dict)
    
    def create_vertiport_manager(self):
        # Create vertiport manager
        return VertiportManager(
            env=self.env,
            vertiports=self.vertiports,
            vertiport_ids=self.vertiport_ids,
            scheduler=self.scheduler,
            arrival_priority=self.sim_params['arrival_priority'],
            departure_priority=self.sim_params['departure_priority'],
            airspace=self.airspace,
            taxi_config=self.taxi_config,
            only_aircraft_simulation=self.sim_params['only_aircraft_simulation'],
            aircraft_params=self.aircraft_params,
            vertiport_distances=self.vertiport_distances,
            aircraft_energy_consumption_data=self.aircraft_energy_consumption_data,
            passenger_distributions=self.passenger_distributions,
            max_flight_waiting_time=self.sim_params['max_passenger_waiting_time'],
            charging_interuption=self.sim_params['charge_interruption'],
            event_saver=self.event_saver,
            network_simulation=self.sim_params['network_simulation'],
            fixed_charge_schedule=check_not_none(self.network_and_demand['charge_schedule_file_name']),
            fixed_schedule=check_not_none(self.network_and_demand['flight_schedule_file_name']),
            flight_rebalancing=self.sim_params['flight_rebalancing'],
            node_locations=self.node_locations,
            flight_duration_constant=sec_to_ms(self.sim_params['flight_duration_constant']),
            logger=self.logger,
            aircraft_logger=self.aircraft_logger,
            passenger_logger=self.passenger_logger
        )

    def create_aircraft_arrival_process(self):
        # Load or generate aircraft arrival schedule and start the aircraft arrival process
        if self.network_and_demand['flight_schedule_file_name'] is not None:
            # Load aircraft arrival schedule
            aircraft_arrival_process = AircraftArrivalSetup(
                env=self.env,
                network_simulation=self.sim_params['network_simulation'],
                vertiport_configs=self.network_and_demand['vertiports'],
                vertiport_layouts=self.vertiport_layouts,
                flight_schedule_file_name=self.network_and_demand['flight_schedule_file_name'],
                charge_schedule_file_name=self.network_and_demand['charge_schedule_file_name'],
                aircraft_params=self.aircraft_params,
                vertiport_manager=self.vertiport_manager,
                scheduler=self.scheduler,
                structural_entity_groups=self.structural_entity_groups,
                event_saver=self.event_saver,
                logger=self.logger,
                aircraft_logger=self.aircraft_logger
            )
        else:
            # Create aircraft arrival process
            aircraft_arrival_process = AircraftArrivalSetup(
                env=self.env,
                network_simulation=self.sim_params['network_simulation'],
                vertiport_layouts=self.vertiport_layouts,                
                vertiport_configs=self.network_and_demand['vertiports'],
                flight_schedule_file_name=None,
                charge_schedule_file_name=None,
                aircraft_params=self.aircraft_params,
                vertiport_manager=self.vertiport_manager,
                scheduler=self.scheduler,
                structural_entity_groups=self.structural_entity_groups,                
                event_saver=self.event_saver,
                logger=self.logger,
                aircraft_logger=self.aircraft_logger
            )
        aircraft_arrival_process.create_aircraft_arrival()

        if self.sim_params['verbose']:
            print("Success: Aircraft arrival process is created.")


    def create_passenger_arrival_process(self):
        if self.sim_params['only_aircraft_simulation'] is False:
            # Load or generate passenger arrival schedule and start the passenger arrival process
            if self.network_and_demand['passenger_schedule_file_name'] is not None:
                passenger_arrival_process = PassengerArrivalSetup(
                    env=self.env,
                    vertiport_configs=self.network_and_demand['vertiports'],
                    passenger_arrival_schedule_file_path=self.network_and_demand[
                        'passenger_schedule_file_name'],
                    passenger_params=self.passenger_params,
                    demand_probabilities=self.network_and_demand['demand_probabilities'],
                    vertiport_ids=self.vertiport_ids,
                    vertiport_manager=self.vertiport_manager,
                    aircraft_params=None,
                    network_simulation=self.sim_params['network_simulation'],
                    passenger_logger=self.passenger_logger
                )
            else:
                # Create passenger arrival process
                passenger_arrival_process = PassengerArrivalSetup(
                    env=self.env,
                    vertiport_configs=self.network_and_demand['vertiports'],
                    passenger_arrival_schedule_file_path=None,
                    passenger_params=self.passenger_params,
                    demand_probabilities=self.network_and_demand['demand_probabilities'],
                    vertiport_ids=self.vertiport_ids,
                    vertiport_manager=self.vertiport_manager,
                    aircraft_params=self.aircraft_params,
                    network_simulation=self.sim_params['network_simulation'],
                    passenger_logger=self.passenger_logger
                )
            self.env.process(
                passenger_arrival_process.create_passenger_arrival()
            )
            if self.sim_params['verbose']:
                print("Success: Passenger arrival process is created.")

    def run_simulation(self):
        max_sim_time = sec_to_ms(self.sim_params['sim_time'])
        if self.sim_params['step_by_step_sim']:
            run_step_by_step_simulation(env=self.env, 
                                        vertiports=self.vertiports, 
                                        airspace=self.airspace,
                                        structural_entity_groups=self.structural_entity_groups,
                                        vertiport_manager=self.vertiport_manager,
                                        max_sim_time=max_sim_time)
        else:
            self.env.run(until=max_sim_time)
        self.print_total_time_to_run()  

    def print_total_time_to_run(self):
        end_time = time.time()
        time_taken = end_time - self.sim_start_time
        print(f'Total time to run: {round(time_taken, 2)} seconds')                      

    def calculate_performance_metrics(self):
        # Print and save performance metrics
        return PerformanceMetrics(sim_start_timestamp=self.sim_start_timestamp,
                                  aircraft_params=self.aircraft_params,
                                  only_aircraft_simulation=self.sim_params['only_aircraft_simulation'],
                                  passenger_consolidation_time=self.event_saver.passenger_consolidation_time,
                                  passenger_departure_queue_count=self.event_saver.passenger_departure_queue_count,
                                  aircraft_arrival_queue_count=self.event_saver.aircraft_arrival_queue_count,
                                  aircraft_departure_queue_count=self.event_saver.aircraft_departure_queue_count,
                                  passenger_waiting_time=self.event_saver.passenger_waiting_time,
                                  passenger_transfer_time=self.event_saver.passenger_transfer_time,
                                  passenger_departure_queue_waiting_time=self.event_saver.passenger_departure_queue_waiting_time,
                                  aircraft_holding_time=self.event_saver.aircraft_holding_time,
                                  aircraft_charging_times=self.event_saver.aircraft_charging_times,
                                  aircraft_taxi_times=self.event_saver.aircraft_taxi_times,
                                  flight_schedule=self.event_saver.flight_schedule,
                                  fato_usage_tracker=self.event_saver.fato_usage_tracker,
                                  aircraft_idle_time_tracker=self.event_saver.aircraft_idle_time_tracker,
                                  flight_and_time_tracker=self.event_saver.flight_and_time_tracker,
                                  flight_count_tracker=self.event_saver.flight_count_tracker,
                                  flight_duration_tracker=self.event_saver.flight_duration_tracker,
                                  load_factor_tracker=self.event_saver.load_factor_tracker,
                                  passenger_count_tracker=self.event_saver.passenger_count_tracker,
                                  passenger_time_tracker=self.event_saver.passenger_time_tracker,
                                  aircraft_energy_consumption_tracker=self.event_saver.aircraft_energy_consumption_tracker,
                                  vertiport_ids=self.vertiport_ids,
                                  sim_id=self.sim_id,
                                  verbose=self.sim_params['verbose']).performance_metrics

    def save_results(self):
        # Save the results
        save_output(
            trackers={
                'aircraft_agent_trajectory': self.event_saver.aircraft_agent_trajectory,
                'passenger_agent_trajectory': self.event_saver.passenger_agent_trajectory,
                'flight_schedule': self.event_saver.flight_schedule,
            },
            simulation_params={
                'sim_params': self.sim_params,
                'network_and_demand': self.network_and_demand,
                'passenger_params': self.passenger_params,
                'aircraft_params': self.aircraft_params,
                'output_params': self.output_params
            },
            output_dir=self.output_folder_path,
            config_output_file_name=self.output_params['config_output_file_name'],
            # aircraft_trajectory_output_file_name=output_params['aircraft_trajectory_output_file_name'],
            # passenger_trajectory_output_file_name=output_params['passenger_trajectory_output_file_name'],
            # flight_schedule_output_file_name=output_params['flight_schedule_output_file_name'],
            performance_metrics_output_file_name=self.output_params['performance_metrics_output_file_name'],
            performance_metrics=self.performance_metrics,
            sim_id=self.sim_id
        )
