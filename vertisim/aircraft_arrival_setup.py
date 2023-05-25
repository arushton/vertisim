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
            
    @staticmethod
    def validate_columns(dataframe: pd.DataFrame, required_columns: list, optional_columns: dict, check_none_columns: list) -> None:
        """
        Validate required columns, optional columns and columns to check for None values.
        :param dataframe: DataFrame to be validated.
        :param required_columns: A list of required column names.
        :param optional_columns: A dictionary of optional column names and their default values.
        :param check_none_columns: A list of column names to check for None values.
        :return: None.
        """
        for column in required_columns:
            # Check if the column exists
            if column not in dataframe.columns:
                raise ValueError(f'{column} column does not exist in the aircraft arrival process file.')
        
        for column in check_none_columns:
            # Check for None values in the column
            if check_if_none_exists(dataframe[column]):
                raise ValueError(f'{column} column has None value.')
        
        for column, default_value in optional_columns.items():
            if column not in dataframe.columns:
                dataframe[column] = default_value
                print(
                    f"{column} is not defined in the input file. The default value of {default_value} is used. If you "
                    "want to define the initial value for each aircraft type, please add the column "
                    f"'{column}' to the input file."
                )

    def check_aircraft_arrival_schedule(self, aircraft_arrival_schedule: pd.DataFrame):
        """
        Check if the columns of the input file are correct.
        :param aircraft_arrival_schedule:
        :return:
        """
        required_columns = [
            'aircraft_arrival_time',
            'aircraft_departure_time',
            'tail_number',
            'origin_vertiport_id',
            'destination_vertiport_id',
            'location',
            'speed'
            # 'passengers_onboard'
        ]
        
        check_none_columns = [
            'aircraft_arrival_time',
            'aircraft_departure_time',
            'tail_number',
            'origin_vertiport_id',
            'destination_vertiport_id',
            # 'passengers_onboard'
        ]
        
        optional_columns = {
            # Column name: default value
            'serviced_time_at_the_location': 0,
            'soc': self.aircraft_params['max_init_soc'],
            'priority': 1,
            'interarrival_time': compute_interarrival_times_from_schedule(aircraft_arrival_schedule['arrival_time'])
        }
        AircraftArrivalSetup.validate_columns(aircraft_arrival_schedule, required_columns, optional_columns, check_none_columns)

            
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
            # Fields to retrieve for each aircraft.
            fields = ['aircraft_departure_time', 'interarrival_time', 'soc', 'speed', 
                    'origin_vertiport_id', 'destination_vertiport_id', 'passengers_onboard', 'location',
                    'serviced_time_at_the_location', 'priority']

            # Create a dictionary to store the retrieved values.
            aircraft_data = {}

            for field in fields:
                # Get the value of the field for the aircraft.
                aircraft_data[field] = aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, field].values[0]

            yield self.env.timeout(sec_to_ms(aircraft_data['interarrival_time']))

            if self.aircraft_arrival_schedule_file_path is not None:
                yield self.env.process(self.scheduler.initiate_fixed_schedule_from_file()) 
            else:
                self.env.process(
                    # Simulate the aircraft.
                    self.initiate_aircraft_arrival(tail_number=tail_number,
                                                soc=aircraft_data['soc'],
                                                input_cruise_speed=aircraft_data['speed'],
                                                origin_vertiport_id=aircraft_data['origin_vertiport_id'],
                                                destination_vertiport_id=aircraft_data['destination_vertiport_id'],
                                                passengers_onboard=aircraft_data['passengers_onboard'],
                                                location=aircraft_data['location'],
                                                serviced_time_at_the_location=aircraft_data['serviced_time_at_the_location'],
                                                departure_time=aircraft_data['aircraft_departure_time'],
                                                priority=aircraft_data['priority'])
                )


    def initiate_aircraft_arrival(self, 
                                  tail_number: str,
                                  soc: int,
                                  input_cruise_speed: int,
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
                            input_cruise_speed=input_cruise_speed,
                            arrival_time=self.env.now,
                            priority=priority,
                            aircraft_params=self.aircraft_params,
                            vertiport_manager=self.vertiport_manager,
                            event_saver=self.event_saver
                            )
        
        self.event_saver.save_agent_state(agent=aircraft, agent_type='aircraft', event='agent_creation')
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
            aircraft.flight_direction = f'{aircraft.origin_vertiport_id}_{aircraft.destination_vertiport_id}'
            yield self.env.process(self.vertiport_manager.departure_fix_request_initial_state(aircraft=aircraft))
        else:
            raise ValueError(f'Unknown aircraft location: {aircraft.location}')