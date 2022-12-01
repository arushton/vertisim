from module_setup import vertiport_config, create_vertiport_manager, create_vertiport_layout, set_taxi_operations_config
from aircraft_arrival_setup import AircraftArrivalSetup
from passenger_arrival_setup import PassengerArrivalSetup
from scheduler import Scheduler
from event_saver import EventSaver
from save_output import save_output
from utils.import_aircraft_energy_consumption_data import import_aircraft_energy_consumption_data
from utils.units import sec_to_ms
from utils.helpers import is_shared_charger
from utils.helpers import set_seed
from utils.setup_distributions import setup_passenger_distributions
from utils.calc_vertiport_distances_from_lat_lng import calc_destination_vertiport_distances
from utils.bundle_passenger_related_distributions import bundle_distributions
# from utils.defaults import sim_params, network_and_demand, vertiport_params, aircraft_params, output_params
import simpy
import random
from typing import Dict, List


def sim_setup(sim_params: dict,
              network_and_demand: dict,
              vertiport_params: dict,
              passenger_params: dict,
              aircraft_params: dict,
              output_params: dict):
    sim_start_timestamp = sec_to_ms(1625065200)  # Wednesday, June 30, 2021 8:00:00 AM PT

    set_seed(sim_params['random_seed'])

    # Create an environment
    env = simpy.Environment()

    # Create vertiport layout
    vertiport_layout = create_vertiport_layout(
        file_path=vertiport_params['vertiport_layout_file_path'],
        layout_type=vertiport_params['layout']
    )
    print("Success: Vertiport layout created.")
    # Create the EventSaver object
    event_saver = EventSaver(env, vertiport_layout, sim_start_timestamp)

    # Import vertiport network
    vertiport_distances = calc_destination_vertiport_distances(network_and_demand['vertiport_network_file_path'])
    print("Success: Vertiport network imported.")

    # Set vertiport configurations
    vertiport = vertiport_config(
        env=env,
        vertiport_layout=vertiport_layout,
        vertiport_distances=vertiport_distances,
        num_chargers=vertiport_params['num_chargers'],
        shared_charger_sets=vertiport_params['shared_charger_sets'],
        num_security_check_servers=vertiport_params['num_security_check_servers']
    )

    # Set taxi operations config
    taxi_config = set_taxi_operations_config(
        is_simultaneous_taxi_and_take_off_allowed=sim_params['simultaneous_taxi_and_take_off']
    )
    print("Success: Vertiport configuration is set.")

    # Import aircraft energy consumption data
    if aircraft_params['aircraft_energy_consumption_data_folder_path'] is not None:
        aircraft_energy_consumption_data = import_aircraft_energy_consumption_data(
            folder_path=aircraft_params['aircraft_energy_consumption_data_folder_path'],
            aircraft_models=network_and_demand['aircraft_arrival_process']['aircraft_fleet_specs'].keys(),
            ranges=list(vertiport_distances.values()))
        print("Success: Aircraft energy consumption data imported.")
    else:
        aircraft_energy_consumption_data = None

    # Bundle passenger related distributions
    passenger_distributions_bundle = bundle_distributions(
        passenger_params['car_to_entrance_walking_time_dist'],
        passenger_params['security_check_time_dist'],
        passenger_params['waiting_room_to_boarding_gate_walking_time_dist'],
        passenger_params['boarding_gate_to_aircraft_time_dist'],
        passenger_params['embark_disembark_time_dist'],
        passenger_params['deboard_aircraft_and_walk_to_exit_dist'],
    )

    # Setup passenger distributions
    passenger_distributions = setup_passenger_distributions(**passenger_distributions_bundle)

    if sim_params['default_aircraft']:
        # Create scheduler
        scheduler = Scheduler(env=env,
                              max_flight_waiting_time=sim_params['max_passenger_waiting_time'],
                              vertiport=vertiport,
                              aircraft_capacity=aircraft_params['pax']
                              )
    else:
        # Create scheduler
        scheduler = Scheduler(env=env,
                              max_flight_waiting_time=sim_params['max_passenger_waiting_time'],
                              vertiport=vertiport,
                              aircraft_fleet_specs=network_and_demand['aircraft_arrival_process']['aircraft_fleet_specs']
                              )

    # Create vertiport manager
    vertiport_manager = create_vertiport_manager(
        env=env,
        vertiport=vertiport,
        scheduler=scheduler,
        arrival_priority=sim_params['arrival_priority'],
        departure_priority=sim_params['departure_priority'],
        taxi_config=taxi_config,
        aircraft_fleet_specs=network_and_demand['aircraft_arrival_process']['aircraft_fleet_specs'],
        aircraft_energy_consumption_data=aircraft_energy_consumption_data,
        charging_time_distribution_params=aircraft_params['charging_time_dist'],
        passenger_distributions=passenger_distributions,
        max_flight_waiting_time=sim_params['max_passenger_waiting_time'],
        charging_interuption=sim_params['interuptive_approach'],
        charger_efficiency=vertiport_params['charger_efficiency'],
        charger_max_charge_rate=vertiport_params['charger_max_charge_rate'],
        min_reserve_soc=aircraft_params['min_reserve_soc'],
        event_saver=event_saver
    )

    # Load or generate aircraft arrival schedule and start the aircraft arrival process
    if network_and_demand['aircraft_arrival_schedule_file_name'] is not None:
        # Load aircraft arrival schedule
        aircraft_arrival_process = AircraftArrivalSetup(
            env=env,
            artificial_aircraft_arrival_process=None,
            aircraft_arrival_schedule_file_path=network_and_demand['aircraft_arrival_schedule_file_name'],
            aircraft_params=aircraft_params,
            vertiport_manager=vertiport_manager,
            event_saver=event_saver
        )
    else:
        # Create aircraft arrival process
        aircraft_arrival_process = AircraftArrivalSetup(
            env=env,
            artificial_aircraft_arrival_process=network_and_demand['aircraft_arrival_process'],
            aircraft_arrival_schedule_file_path=None,
            aircraft_params=aircraft_params,
            vertiport_manager=vertiport_manager,
            event_saver=event_saver
        )
    env.process(
        aircraft_arrival_process.create_aircraft_arrival()
    )
    print("Success: Aircraft arrival process is created.")

    if sim_params['only_aircraft_simulation'] is False:
        # Load or generate passenger arrival schedule and start the passenger arrival process
        if network_and_demand['passenger_arrival_schedule_file_name'] is not None:
            passenger_arrival_process = PassengerArrivalSetup(
                env=env,
                artificial_passenger_arrival_process=None,
                passenger_arrival_schedule_file_path=network_and_demand['passenger_arrival_schedule_file_name'],
                passenger_params=passenger_params,
                flight_destination_ids=list(vertiport_distances.keys()),
                vertiport_manager=vertiport_manager
            )
        else:
            # Create passenger arrival process
            passenger_arrival_process = PassengerArrivalSetup(
                env=env,
                artificial_passenger_arrival_process=network_and_demand['passenger_arrival_process'],
                passenger_arrival_schedule_file_path=None,
                passenger_params=passenger_params,
                flight_destination_ids=list(vertiport_distances.keys()),
                vertiport_manager=vertiport_manager
            )
        env.process(
            passenger_arrival_process.create_passenger_arrival()
        )
        print("Success: Passenger arrival process is created.")

    # Run the simulation
    max_sim_time = sec_to_ms(sim_params['sim_time'])
    env.run(until=max_sim_time)

    # Save the results
    save_output(
        trackers={
            # 'aircraft_dict': event_saver.aircraft_dict,
            # 'aircraft_dict_w_sim_time': event_saver.aircraft_dict_w_sim_time,
            'aircraft_agent_trajectory': event_saver.aircraft_agent_trajectory,
            'passenger_agent_trajectory': event_saver.passenger_agent_trajectory
        },
        simulation_params={
            'sim_params': sim_params,
            'network_and_demand': network_and_demand,
            'vertiport_params': vertiport_params,
            'passenger_params': passenger_params,
            'aircraft_params': aircraft_params,
            'output_params': output_params
        },
        output_dir=output_params['output_folder_path'],
        config_output_file_name=output_params['config_output_file_name'],
        aircraft_trajectory_output_file_name=output_params['aircraft_trajectory_output_file_name'],
        passenger_trajectory_output_file_name=output_params['passenger_trajectory_output_file_name']
    )
