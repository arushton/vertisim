import random
import string
import time

# from utils.defaults import sim_params, network_and_demand, vertiport_params, aircraft_params, output_params
import simpy

from aircraft_arrival_setup import AircraftArrivalSetup
from event_saver import EventSaver
from module_setup import vertiport_config, create_vertiport_manager, create_vertiport_layout, set_taxi_operations_config
from passenger_arrival_setup import PassengerArrivalSetup
from performance_metrics import PerformanceMetrics
from save_output import save_output
from scheduler import Scheduler
from utils.bundle_passenger_related_distributions import bundle_distributions
from utils.calc_vertiport_distances_from_lat_lng import calc_destination_vertiport_distances
from utils.helpers import set_seed
from utils.import_aircraft_energy_consumption_data import import_aircraft_energy_consumption_data
from utils.setup_distributions import setup_passenger_distributions
from utils.units import sec_to_ms


class SimSetup:
    def __init__(self,
                 sim_params,
                 network_and_demand: dict,
                 vertiport_params: dict,
                 passenger_params: dict,
                 aircraft_params: dict,
                 output_params: dict,
                 sim_start_time: int):
        self.sim_params = sim_params
        self.network_and_demand = network_and_demand
        self.vertiport_params = vertiport_params
        self.passenger_params = passenger_params
        self.aircraft_params = aircraft_params
        self.output_params = output_params
        self.sim_start_time = sim_start_time

        self.sim_start_timestamp = sec_to_ms(1625065200)  # Wednesday, June 30, 2021 8:00:00 AM PT
        set_seed(sim_params['random_seed'])
        self.env = self.create_environment()
        self.vertiport_layout = self.create_vertiport_layout()
        self.event_saver = self.create_event_saver()
        self.vertiport_distances = self.import_vertiport_distance()
        self.vertiport = self.create_vertiport()
        self.taxi_config = self.set_taxi_operations_config()
        self.aircraft_energy_consumption_data = self.set_aircraft_energy_consumption_data()
        self.passenger_distributions = self.create_passenger_distributions()
        self.scheduler = self.create_scheduler()
        self.vertiport_manager = self.create_vertiport_manager()

        self.create_aircraft_arrival_process()
        self.create_passenger_arrival_process()
        self.run_simulation()

        self.sim_id = self.set_sim_id()
        self.performance_metrics = self.calculate_performance_metrics()
        self.save_results()

    def create_environment(self):
        """
        Creates the environment
        """
        return simpy.Environment()

    def create_vertiport_layout(self):
        """
        Creates the vertiport layout
        """
        # Create vertiport layout
        vertiport_layout = create_vertiport_layout(
            file_path=self.vertiport_params['vertiport_layout_file_path'],
            layout_type=self.vertiport_params['layout']
        )
        if self.sim_params['verbose']:
            print("Success: Vertiport layout created.")
        return vertiport_layout

    def create_event_saver(self):
        """
        Creates the event saver
        """
        # Create event saver
        return EventSaver(self.env, self.vertiport_layout, self.sim_start_timestamp)

    def import_vertiport_distance(self):
        """
        Imports the vertiport distance
        """
        # Import vertiport distance
        vertiport_distances = calc_destination_vertiport_distances(
            self.network_and_demand['vertiport_network_file_path'])
        if self.sim_params['verbose']:
            print("Success: Vertiport network imported.")
        return vertiport_distances

    def create_vertiport(self):
        # Set vertiport configurations
        return vertiport_config(
            env=self.env,
            vertiport_layout=self.vertiport_layout,
            vertiport_distances=self.vertiport_distances,
            num_chargers=self.vertiport_params['num_chargers'],
            shared_charger_sets=self.vertiport_params['shared_charger_sets'],
            num_security_check_servers=self.vertiport_params['num_security_check_servers']
        )

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

    def import_aircraft_energy_consumption_data(self):
        """
        Imports the aircraft energy consumption data
        """
        # Import aircraft energy consumption data
        if self.aircraft_params['aircraft_energy_consumption_data_folder_path'] is not None:
            aircraft_energy_consumption_data = import_aircraft_energy_consumption_data(
                folder_path=self.aircraft_params['aircraft_energy_consumption_data_folder_path'],
                aircraft_models=self.network_and_demand['aircraft_arrival_process']['aircraft_fleet_specs'].keys(),
                ranges=list(self.vertiport_distances.values()))
            if self.sim_params['verbose']:
                print("Success: Aircraft energy consumption data imported.")
        else:
            aircraft_energy_consumption_data = None
        return aircraft_energy_consumption_data

    def set_aircraft_energy_consumption_data(self):
        """
        Sets the aircraft energy consumption data
        """
        if self.sim_params['battery_model_sim']:
            return self.import_aircraft_energy_consumption_data()
        else:
            return None

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
        if self.sim_params['default_aircraft']:
            # Create scheduler
            return Scheduler(env=self.env,
                             vertiport=self.vertiport,
                             aircraft_capacity=self.aircraft_params['pax']
                             )
        else:
            # Create scheduler
            return Scheduler(env=self.env,
                             vertiport=self.vertiport,
                             aircraft_fleet_specs=self.network_and_demand['aircraft_arrival_process'][
                                 'aircraft_fleet_specs']
                             )

    def create_vertiport_manager(self):
        # Create vertiport manager
        return create_vertiport_manager(
            env=self.env,
            vertiport=self.vertiport,
            scheduler=self.scheduler,
            arrival_priority=self.sim_params['arrival_priority'],
            departure_priority=self.sim_params['departure_priority'],
            taxi_config=self.taxi_config,
            only_aircraft_simulation=self.sim_params['only_aircraft_simulation'],
            aircraft_fleet_specs=self.network_and_demand['aircraft_arrival_process']['aircraft_fleet_specs'],
            aircraft_energy_consumption_data=self.aircraft_energy_consumption_data,
            charging_time_distribution_params=self.aircraft_params['charging_time_dist'],
            passenger_distributions=self.passenger_distributions,
            max_flight_waiting_time=self.sim_params['max_passenger_waiting_time'],
            charging_interuption=self.sim_params['interuptive_approach'],
            charger_efficiency=self.vertiport_params['charger_efficiency'],
            charger_max_charge_rate=self.vertiport_params['charger_max_charge_rate'],
            min_reserve_soc=self.aircraft_params['min_reserve_soc'],
            event_saver=self.event_saver
        )

    def create_aircraft_arrival_process(self):
        # Load or generate aircraft arrival schedule and start the aircraft arrival process
        if self.network_and_demand['aircraft_arrival_schedule_file_name'] is not None:
            # Load aircraft arrival schedule
            aircraft_arrival_process = AircraftArrivalSetup(
                env=self.env,
                artificial_aircraft_arrival_process=None,
                aircraft_arrival_schedule_file_path=self.network_and_demand['aircraft_arrival_schedule_file_name'],
                aircraft_params=self.aircraft_params,
                vertiport_manager=self.vertiport_manager,
                event_saver=self.event_saver
            )
        else:
            # Create aircraft arrival process
            aircraft_arrival_process = AircraftArrivalSetup(
                env=self.env,
                artificial_aircraft_arrival_process=self.network_and_demand['aircraft_arrival_process'],
                aircraft_arrival_schedule_file_path=None,
                aircraft_params=self.aircraft_params,
                vertiport_manager=self.vertiport_manager,
                event_saver=self.event_saver
            )
        self.env.process(
            aircraft_arrival_process.create_aircraft_arrival()
        )
        if self.sim_params['verbose']:
            print("Success: Aircraft arrival process is created.")

    def create_passenger_arrival_process(self):
        if self.sim_params['only_aircraft_simulation'] is False:
            # Load or generate passenger arrival schedule and start the passenger arrival process
            if self.network_and_demand['passenger_arrival_schedule_file_name'] is not None:
                passenger_arrival_process = PassengerArrivalSetup(
                    env=self.env,
                    artificial_passenger_arrival_process=None,
                    passenger_arrival_schedule_file_path=self.network_and_demand[
                        'passenger_arrival_schedule_file_name'],
                    passenger_params=self.passenger_params,
                    flight_destination_ids=list(self.vertiport_distances.keys()),
                    vertiport_manager=self.vertiport_manager
                )
            else:
                # Create passenger arrival process
                passenger_arrival_process = PassengerArrivalSetup(
                    env=self.env,
                    artificial_passenger_arrival_process=self.network_and_demand['passenger_arrival_process'],
                    passenger_arrival_schedule_file_path=None,
                    passenger_params=self.passenger_params,
                    flight_destination_ids=list(self.vertiport_distances.keys()),
                    vertiport_manager=self.vertiport_manager
                )
            self.env.process(
                passenger_arrival_process.create_passenger_arrival()
            )
            if self.sim_params['verbose']:
                print("Success: Passenger arrival process is created.")

    def run_simulation(self):
        # Run the simulation
        max_sim_time = sec_to_ms(self.sim_params['sim_time'])
        self.env.run(until=max_sim_time)

        end_time = time.time()
        time_taken = end_time - self.sim_start_time
        # print(f'Total time to run: {round(time_taken, 2)} seconds')

    def set_sim_id(self):
        # Set simulation id
        random.seed(round(time.time()))
        return ''.join(random.choices(string.ascii_uppercase, k=8))

    def calculate_performance_metrics(self):
        # Print and save performance metrics
        return PerformanceMetrics(sim_start_timestamp=self.sim_start_timestamp,
                                  only_aircraft_simulation=self.sim_params['only_aircraft_simulation'],
                                  passenger_consolidation_time=self.event_saver.passenger_consolidation_time,
                                  passenger_departure_queue_count=self.event_saver.passenger_departure_queue_count,
                                  aircraft_arrival_queue_count=self.event_saver.aircraft_arrival_queue_count,
                                  aircraft_departure_queue_count=self.event_saver.aircraft_departure_queue_count,
                                  passenger_waiting_time=self.event_saver.passenger_waiting_time,
                                  passenger_transfer_time=self.event_saver.passenger_transfer_time,
                                  flight_schedule=self.event_saver.flight_schedule,
                                  fato_usage_tracker=self.event_saver.fato_usage_tracker,
                                  sim_id=self.sim_id,
                                  verbose=self.sim_params['verbose'])

    def save_results(self):
        # Save the results
        save_output(
            trackers={
                'aircraft_agent_trajectory': self.event_saver.aircraft_agent_trajectory,
                'passenger_agent_trajectory': self.event_saver.passenger_agent_trajectory,
                # 'aircraft_queue_count': event_saver.aircraft_queue_count,
                # 'passenger_queue_count': event_saver.passenger_queue_count,
                'flight_schedule': self.event_saver.flight_schedule,
            },
            simulation_params={
                'sim_params': self.sim_params,
                'network_and_demand': self.network_and_demand,
                'vertiport_params': self.vertiport_params,
                'passenger_params': self.passenger_params,
                'aircraft_params': self.aircraft_params,
                'output_params': self.output_params
            },
            output_dir=self.output_params['output_folder_path'],
            config_output_file_name=self.output_params['config_output_file_name'],
            # aircraft_trajectory_output_file_name=output_params['aircraft_trajectory_output_file_name'],
            # passenger_trajectory_output_file_name=output_params['passenger_trajectory_output_file_name'],
            # flight_schedule_output_file_name=output_params['flight_schedule_output_file_name'],
            performance_metrics_output_file_name=self.output_params['performance_metrics_output_file_name'],
            performance_metrics=self.performance_metrics.performance_metrics,
            sim_id=self.sim_id
        )
