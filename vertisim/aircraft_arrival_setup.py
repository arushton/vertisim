import pandas as pd

from aircraft import Aircraft
import pandas as pd
from utils.units import sec_to_ms
from utils.helpers import compute_interarrival_times_from_schedule, check_if_none_exists
from utils.generate_artificial_supply_demand import generate_aircraft_network_schedule
# from utils.defaults import DEFAULT_AIRCRAFT_ARRIVAL_PROCESS
from typing import Dict, List, Union
from utils.read_files import read_input_file
# from utils.create_arrival_process import create_aircraft_arrival_process


class AircraftArrivalSetup:
    def __init__(self,
                 env: object,
                 network_simulation: bool,
                 vertiport_layouts: Dict,
                 vertiport_configs: Union[Dict, None],
                 aircraft_arrival_schedule_file_path: Union[str, None],
                 aircraft_params: Dict,
                 vertiport_manager: int,
                 scheduler: object,
                 structural_entity_groups: Dict,                
                 event_saver: object):
        self.env = env
        self.network_simulation = network_simulation
        self.vertiport_layouts = vertiport_layouts
        self.aircraft_arrival_schedule_file_path = aircraft_arrival_schedule_file_path
        self.vertiport_configs = vertiport_configs
        self.aircraft_params = aircraft_params
        self.vertiport_manager = vertiport_manager
        self.scheduler = scheduler
        self.structural_entity_groups = structural_entity_groups
        self.event_saver = event_saver
        self.num_aircraft = None

    def check_aircraft_arrival_schedule(self, aircraft_arrival_schedule: pd.DataFrame):
        """
        Check if the columns of the input file are correct.
        :param aircraft_arrival_schedule:
        :return:
        """
        # Check if aircraft arrival time exists in the input file.
        if 'aircraft_arrival_time' not in aircraft_arrival_schedule.columns:
            raise ValueError('aircraft_arrival_time column is not exist in the aircraft arrival process file.')

        # Check if there is any None value on the aircraft arrival time column.
        if check_if_none_exists(aircraft_arrival_schedule['aircraft_arrival_time']):
            raise ValueError('aircraft_arrival_time column has None value.')

        # Check if aircraft departure time exists in the input file.
        if 'aircraft_departure_time' not in aircraft_arrival_schedule.columns:
            raise ValueError('aircraft_departure_time column is not exist in the aircraft arrival process file.')

        # Check if there is any None values exists in the aircraft_departure_time column.
        if check_if_none_exists(aircraft_arrival_schedule['aircraft_departure_time']):
            raise ValueError('aircraft_departure_time column has None value.')

        # Check if tail number exists in the input file.
        if 'tail_number' not in aircraft_arrival_schedule.columns:
            raise ValueError('tail_number column is not exist in the aircraft arrival process file.')
        
        # Check None values in the tail number column.
        if check_if_none_exists(aircraft_arrival_schedule['tail_number']):
            raise ValueError('tail_number column has None value.')

        # Check if vertiport_id column exists in the input file.
        if 'origin_vertiport_id' not in aircraft_arrival_schedule.columns:
            raise ValueError('origin_vertiport_id column is not exist in the aircraft arrival process file.')
        
        # Check None values in the vertiport_id column.
        if check_if_none_exists(aircraft_arrival_schedule['origin_vertiport_id']):
            raise ValueError('origin_vertiport_id column has None value.')

        # Check if destination_vertiport_id column exists in the input file.
        if 'destination_vertiport_id' not in aircraft_arrival_schedule.columns:
            raise ValueError('destination_vertiport_id column is not exist in the aircraft arrival process file.')
        
        # Check None values in the destination_vertiport_id column.
        if check_if_none_exists(aircraft_arrival_schedule['destination_vertiport_id']):
            raise ValueError('destination_vertiport_id column has None value.')

        # Check if passengers_onboard column exists in the input file.
        if 'passengers_onboard' not in aircraft_arrival_schedule.columns:
            raise ValueError('passengers_onboard column is not exist in the aircraft arrival process file.')
        
        # Check None values in the passengers_onboard column.
        if check_if_none_exists(aircraft_arrival_schedule['passengers_onboard']):
            raise ValueError('passengers_onboard column has None value.')

        # Check if location column exists in the input file.
        if 'location' not in aircraft_arrival_schedule.columns:
            raise ValueError('location column is not exist in the aircraft arrival process file.')
        
        # Check None values in the location column.
        if check_if_none_exists(aircraft_arrival_schedule['location']):
            raise ValueError('location column has None value.')

        # Check if serviced_time_at_the_location column exists in the input file.
        if 'serviced_time_at_the_location' not in aircraft_arrival_schedule.columns:
            aircraft_arrival_schedule['serviced_time_at_the_location'] = 0
            print(
                "serviced_time_at_the_location is not defined in the input file. The default serviced_time_at_the_location of 0 is used. If you want to define the serviced_time_at_the_location for each aircraft type, please add the column 'serviced_time_at_the_location' to the input file."
            )

        # Check if initial state of charge exists in the input file.
        if 'soc' not in aircraft_arrival_schedule.columns:
            aircraft_arrival_schedule['soc'] = self.aircraft_params['max_init_soc']
            print(
                f"State of charge is not defined in the input file. The default initial state of charge of {self.aircraft_params['max_init_soc']} is used. If you "
                "want to define the initial state of charge for each aircraft type, please add the column "
                "'max_init_soc' to the input file.")
        
        # Check if priority exists in the input file.
        if 'priority' not in aircraft_arrival_schedule.columns:
            aircraft_arrival_schedule['priority'] = 1
            print(
                f"Priority is not defined in the input file. The default priority of 1 is used. If you "
                "want to define the priority for each aircraft type, please add the column "
                "'priority' to the input file.")

        # Check if interarrival column time exists in the input file.
        if 'interarrival_time' not in aircraft_arrival_schedule.columns:
            aircraft_arrival_schedule['interarrival_time'] = compute_interarrival_times_from_schedule(
                aircraft_arrival_schedule['arrival_time'])
            
    def setup_aircraft_arrival(self):
        if self.aircraft_arrival_schedule_file_path is not None:
            # Load aircraft arrival schedule from the path provided on self.aircraft_arrival_schedule.
            aircraft_arrival_schedule_from_file = read_input_file(self.aircraft_arrival_schedule_file_path)
            # Sort the aircraft arrival schedule by arrival time.
            aircraft_arrival_schedule_from_file = aircraft_arrival_schedule_from_file.sort_values(by='aircraft_arrival_time')
            # Check if the columns of the input file are correct.
            self.check_aircraft_arrival_schedule(aircraft_arrival_schedule_from_file)
            # We get the initial state of the system from the input file. The rest will be used from aircraft_arrival_schedule
            first_events = aircraft_arrival_schedule.groupby('tail_number').first()
            # Exclude the first events from the aircraft arrival schedule.
            aircraft_arrival_schedule_from_file = pd.concat([aircraft_arrival_schedule_from_file, first_events, first_events]).drop_duplicates(keep=False)
            # Save the aircraft arrival schedule for the scheduler.
            self.scheduler.fixed_flight_schedule = aircraft_arrival_schedule_from_file
            self.scheduler.vertiport_manager = self.vertiport_manager

            print("Success: Aircraft arrival schedule loaded from file.")
            return first_events
        else:
            # Generate artificial aircraft arrival schedule.
            aircraft_arrival_schedule = generate_aircraft_network_schedule(
                vertiport_configs=self.vertiport_configs,
                vertiport_layouts=self.vertiport_layouts,
                aircraft_params=self.aircraft_params,
                network_simulation=self.network_simulation)
            # Get the number of aircraft.
            self.num_aircraft = len(aircraft_arrival_schedule)
            return aircraft_arrival_schedule

    def create_aircraft_arrival(self):
        # Create aircraft arrival process.
        aircraft_arrival_schedule = self.setup_aircraft_arrival()

        for tail_number in aircraft_arrival_schedule.tail_number:
            # Get the departure time of the aircraft.
            departure_time = aircraft_arrival_schedule.loc[aircraft_arrival_schedule.tail_number == tail_number,
                                                                'aircraft_departure_time'].values[0]

            # Get the interarrival time of the aircraft.
            interarrival_time = aircraft_arrival_schedule.loc[aircraft_arrival_schedule.tail_number == tail_number,
                                                              'interarrival_time'].values[0]
            # Get the initial state of charge of the aircraft.
            soc = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'soc'].values[0]
            
            speed = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'speed'].values[0]
            
            # Get the arrival vertiport id of the aircraft.
            origin_vertiport_id = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'origin_vertiport_id'].values[0]
            
            # Get the destination vertiport id of the aircraft.
            destination_vertiport_id = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'destination_vertiport_id'].values[0]
            
            # Get the passengers onboard of the aircraft.
            passengers_onboard = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'passengers_onboard'].values[0]
            
            # Get the initial location of the aircraft.
            location = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'location'].values[0]
            
            # Get the serviced time at the location
            serviced_time_at_the_location = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'serviced_time_at_the_location'].values[0]
        
            # Get the priority of the aircraft.
            priority = \
                aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, 'priority'].values[0]

            yield self.env.timeout(sec_to_ms(interarrival_time))

            # TODO: Agent should be created anywhere in the simulation. vertiport_id key should be changed to location_id.
            self.event_saver.save_agent_location(agent_id=tail_number,
                                                 location_id=location,
                                                 agent_type='aircraft')
                    
            if self.aircraft_arrival_schedule_file_path is not None:
                yield self.env.process(self.scheduler.initiate_fixed_schedule_from_file()) 
            else:
                yield self.env.process(                   
                # Simulate the aircraft.
                self.initiate_aircraft_arrival(tail_number=tail_number,
                                            soc=soc,
                                            speed=speed,
                                            origin_vertiport_id=origin_vertiport_id,
                                            destination_vertiport_id=destination_vertiport_id,
                                            passengers_onboard=passengers_onboard,
                                            location=location,
                                            serviced_time_at_the_location=serviced_time_at_the_location,
                                            departure_time=departure_time,
                                            priority=priority)
                )



    def initiate_aircraft_arrival(self, 
                                  tail_number: str,
                                  soc: int,
                                  speed: int,
                                  origin_vertiport_id: str,
                                  destination_vertiport_id: str,
                                  passengers_onboard: List,
                                  location: str,
                                  serviced_time_at_the_location: int,
                                  departure_time: int,
                                  priority: int):

        aircraft = Aircraft(env=self.env,
                            tail_number=tail_number,
                            origin_vertiport_id=origin_vertiport_id,
                            destination_vertiport_id=destination_vertiport_id,
                            passengers_onboard=passengers_onboard,
                            location=location,
                            serviced_time_at_the_location=serviced_time_at_the_location,
                            departure_time=departure_time,
                            soc=soc,
                            speed=speed,
                            arrival_time=self.env.now,
                            priority=priority,
                            aircraft_params=self.aircraft_params,
                            vertiport_manager=self.vertiport_manager,
                            event_saver=self.event_saver
                            )
        
        # Save aircraft in aircraft_agent dictionary.
        self.vertiport_manager.aircraft_agents[f'tail_number_{aircraft.tail_number}'] = aircraft

        # Based on aircraft initial location, initiate the related process.    
        if aircraft.location in self.structural_entity_groups['fato']:
            aircraft.assigned_fato_id = aircraft.location
            yield self.env.process(self.vertiport_manager.fato_and_parking_pad_usage_process(aircraft=aircraft))
        elif aircraft.location in self.structural_entity_groups['parking_pad']:
            aircraft.parking_space_id = aircraft.location
            yield self.env.process(self.vertiport_manager.fato_and_parking_pad_usage_process(aircraft=aircraft))
        elif aircraft.location in self.structural_entity_groups['approach_fix_node']:
            yield self.env.process(self.vertiport_manager.simulate_terminal_airspace_arrival_process(aircraft=aircraft,
                                                                                               arriving_passengers=passengers_onboard))
        elif aircraft.location in self.structural_entity_groups['departure_fix_node']:
            yield self.env.process(self.vertiport_manager.departure_fix_request_initial_state(aircraft=aircraft,
                                                                                              flight_direction=f'{aircraft.origin_vertiport_id}_{aircraft.destination_vertiport_id}'))
        else:
            raise ValueError(f'Unknown aircraft location: {aircraft.location}')