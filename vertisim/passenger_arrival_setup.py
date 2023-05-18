from typing import Dict, Union, List, Any
import pandas as pd
from utils.read_files import read_input_file
from utils.helpers import compute_interarrival_times_from_schedule
from utils.generate_artificial_supply_demand import generate_passenger_network_demand
from utils.units import sec_to_ms
from passenger import Passenger


class PassengerArrivalSetup:
    def __init__(self,
                 env: object,
                 vertiport_configs: Dict,
                 passenger_arrival_schedule_file_path: Union[str, None],
                 passenger_params: Dict,
                 demand_probabilities: List,
                 vertiport_ids: List,
                 vertiport_manager: int,
                 aircraft_params: Dict = None,
                 network_simulation: bool = False):
        self.env = env
        self.passenger_arrival_schedule_file_path = passenger_arrival_schedule_file_path
        self.vertiport_configs = vertiport_configs
        self.passenger_params = passenger_params
        self.demand_probabilities = demand_probabilities
        self.vertiport_ids = vertiport_ids
        self.vertiport_manager = vertiport_manager
        self.aircraft_params = aircraft_params
        self.network_simulation = network_simulation

    @staticmethod
    def check_passenger_arrival_schedule(passenger_arrival_schedule: pd.DataFrame):
        # Check if passenger ID column exists.
        if 'passenger_id' not in passenger_arrival_schedule.columns:
            raise ValueError('Passenger arrival schedule must have a column named passenger_id.')
        # Check if passenger arrival time column exists.
        if 'passenger_arrival_time' not in passenger_arrival_schedule.columns:
            raise ValueError('Passenger arrival schedule must have a column named passenger_arrival_time.')
        # Check if arrival vertiport id column exists.
        if 'origin_vertiport_id' not in passenger_arrival_schedule.columns:
            raise ValueError('Passenger arrival schedule must have a column named origin_vertiport_id.')
        # Check if passenger destination vertiport ID column exists.
        if 'destination_vertiport_id' not in passenger_arrival_schedule.columns:
            raise ValueError('Passenger arrival schedule must have a column named destination_vertiport_id.')
        # Check if passenger interarrival time column exists.
        if 'interarrival_time' not in passenger_arrival_schedule.columns:
            passenger_arrival_schedule['interarrival_time'] = compute_interarrival_times_from_schedule(passenger_arrival_schedule['passenger_arrival_time'])

    def setup_passenger_arrival(self):
        if self.passenger_arrival_schedule_file_path is not None:
            # Load passenger arrival schedule from the path provided on self.passenger_arrival_schedule.
            passenger_arrival_schedule = read_input_file(self.passenger_arrival_schedule_file_path)
            # Check if the columns of the input file are correct.
            self.check_passenger_arrival_schedule(passenger_arrival_schedule)
            print("Success: Passenger arrival schedule loaded from file.")
        else:
            # Generate artificial passenger arrival schedule.
            passenger_arrival_schedule = generate_passenger_network_demand(
                vertiport_configs=self.vertiport_configs,
                vertiport_ids=self.vertiport_ids,
                demand_probabilities=self.demand_probabilities,
                network_simulation=self.network_simulation
            )
            # print("Success: Passenger arrival schedule is generated from the given distribution.")
        return passenger_arrival_schedule

    def create_passenger_arrival(self):
        # Setup passenger arrival schedule.
        passenger_arrival_schedule = self.setup_passenger_arrival()

        if not self.network_simulation:
            if self.aircraft_params['time_charging']:
                charging_time = self.aircraft_params['time_charging']
            else:
                charging_time = self.aircraft_params['charging_time_dist']['parameters']['scale']

            origin_vertiport_id = list(self.vertiport_configs.keys())[0]
            # Time to fill the vertiport with aircraft. This number is inputed in sim_params['initial_parking_occupancy']
            if self.vertiport_configs[origin_vertiport_id]['passenger_arrival_process']['passenger_interarrival_constant'] is not None:
                passenger_arrival_interval_time = self.vertiport_configs[origin_vertiport_id]['passenger_arrival_process']['passenger_interarrival_constant']
            else:
                passenger_arrival_interval_time = self.vertiport_configs[origin_vertiport_id]['passenger_arrival_process']['passenger_arrival_distribution']['parameters']['scale']   
            num_parking_pads = self.vertiport_manager.vertiports[origin_vertiport_id].vertiport_layout.num_parking_pad # This is the number of parking pads at the first vertiport. Might be improved.
            time_to_fill_vertiport = int(num_parking_pads/2) * (
                self.aircraft_params['time_descend_transition'] +
                self.aircraft_params['time_hover_descend'] +
                self.aircraft_params['time_rotor_spin_down'] +
                22) + charging_time - self.aircraft_params['pax']/2 * passenger_arrival_interval_time
            time_to_fill_vertiport = max(0, time_to_fill_vertiport)

            yield self.env.timeout(sec_to_ms(time_to_fill_vertiport))

        # Create passenger arrival process.
        for passenger_id in passenger_arrival_schedule.passenger_id:
            # Get the passenger's interarrival time
            interarrival_time = passenger_arrival_schedule.loc[passenger_arrival_schedule.passenger_id == passenger_id, 'interarrival_time'].values[0]
            # Get the passenger's origin vertiport id
            origin_vertiport_id = passenger_arrival_schedule.loc[passenger_arrival_schedule.passenger_id == passenger_id, 'origin_vertiport_id'].values[0]
            # Get the passenger's destination vertiport id
            dest_vertiport_id = passenger_arrival_schedule.loc[passenger_arrival_schedule.passenger_id == passenger_id, 'dest_vertiport_id'].values[0]
            # Get the location of the passenger
            passenger_location = f'{origin_vertiport_id}_ENTRANCE'

            yield self.env.timeout(sec_to_ms(interarrival_time))
            # print(f'Passenger {passenger_id} arrives at {int((self.env.now)/1000/60)}')
            # Simulate passenger.
            self.initiate_passenger_arrival(
                    passenger_id=passenger_id,
                    location=passenger_location,
                    origin_vertiport_id=origin_vertiport_id,
                    dest_vertiport_id=dest_vertiport_id
            )

    def initiate_passenger_arrival(self, 
                                   passenger_id: int,
                                   location: str,
                                   origin_vertiport_id: Any,
                                   dest_vertiport_id: Any):
        # Create a passenger object
        passenger = Passenger(
            env=self.env,
            passenger_id=passenger_id,
            location=location,
            origin_vertiport_id=origin_vertiport_id,
            dest_vertiport_id=dest_vertiport_id,
            car_to_entrance_walking_time_constant=sec_to_ms(self.passenger_params['car_to_entrance_walking_time_constant']),
            security_check_time_constant=sec_to_ms(self.passenger_params['security_check_time_constant']),
            waiting_room_to_boarding_gate_walking_time_constant=sec_to_ms(self.passenger_params['waiting_room_to_boarding_gate_walking_time_constant']),
            boarding_gate_to_aircraft_time_constant=sec_to_ms(self.passenger_params['boarding_gate_to_aircraft_time_constant']),
            embark_disembark_time_constant=sec_to_ms(self.passenger_params['embark_disembark_time_constant']),
            deboard_aircraft_and_walk_to_exit_constant=sec_to_ms(self.passenger_params['deboard_aircraft_and_walk_to_exit_constant']),
            randomize_constants=self.passenger_params['randomize_constants'],
            vertiport_manager=self.vertiport_manager
        )

        # Add passenger to the passenger agents dictionary.
        self.vertiport_manager.passenger_agents[f'passenger_{passenger_id}'] = passenger
        # Initiate passenger arrival.
        self.env.process(self.vertiport_manager.simulate_passenger_arrival(passenger))
