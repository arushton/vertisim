import pandas as pd

from aircraft.aircraft import Aircraft
import pandas as pd
from utils.units import sec_to_ms
from utils.helpers import compute_interarrival_times_from_schedule, check_if_none_exists, careful_conversion
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
        :return: dataframe.
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
        return dataframe
                # if column not in ['interarrival_time', 'passengers_onboard']:
                #     print(
                #         f"{column} is not defined in the input file. The default value of {default_value} is used. If you "
                #         "want to define the initial value for each aircraft type, please add the column "
                #         f"'{column}' to the input file."
                #     )

    def check_aircraft_arrival_schedule(self, aircraft_arrival_schedule: pd.DataFrame):
        """
        Check if the columns of the input file are correct.
        :param aircraft_arrival_schedule:
        :return:
        """
        required_columns = [
            'aircraft_arrival_time',
            'aircraft_pushback_time',
            'tail_number',
            'origin_vertiport_id',
            'destination_vertiport_id',
            'location'
            # 'passengers_onboard'
        ]
        
        check_none_columns = [
            'aircraft_arrival_time',
            'aircraft_pushback_time',
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
            'passengers_onboard': [[] for _ in range(len(aircraft_arrival_schedule))],
            'interarrival_time': compute_interarrival_times_from_schedule(aircraft_arrival_schedule['aircraft_arrival_time']),
            'pushback_interarrival_time': compute_interarrival_times_from_schedule(aircraft_arrival_schedule['aircraft_pushback_time'])
        }
        return AircraftArrivalSetup.validate_columns(aircraft_arrival_schedule, required_columns, optional_columns, check_none_columns)

        
    def setup_aircraft_arrival(self):
        if self.aircraft_arrival_schedule_file_path is not None:
            return self._load_schedule_from_file()
        else:
            return self._generate_artificial_schedule()

    def _load_schedule_from_file(self):
        # Load and process aircraft arrival schedule
        schedule, initial_states = self._read_and_process_schedule(self.aircraft_arrival_schedule_file_path)

        # Set up scheduler with the processed schedule
        self._setup_scheduler_with_schedule(schedule)

        print("Success: Aircraft arrival schedule loaded from file.")
        return initial_states

    def _generate_artificial_schedule(self):
        # Generate artificial aircraft arrival schedule
        schedule = generate_aircraft_network_schedule(
            vertiport_configs=self.vertiport_configs,
            vertiport_layouts=self.vertiport_layouts,
            aircraft_params=self.aircraft_params,
            network_simulation=self.network_simulation)

        # Get the number of aircraft
        self.num_aircraft = len(schedule)
        return schedule

    def _read_and_process_schedule(self, path):
        # Load aircraft arrival schedule from the path and sort by arrival time
        schedule = read_input_file(path).sort_values(by='aircraft_arrival_time')

        # Check if the columns of the input file are correct
        schedule = self.check_aircraft_arrival_schedule(schedule)

        # Convert the columns to milliseconds
        schedule = self.convert_schedule_columns_to_ms(schedule)

        # Get the initial state of the system from the input file
        initial_states = self._get_initial_system_state(schedule)
        return schedule, initial_states

    def _get_initial_system_state(self, schedule):
        first_events = schedule.groupby('tail_number').first().reset_index()
        first_events['destination_vertiport_id'] = first_events['origin_vertiport_id']
        return first_events

    def _setup_scheduler_with_schedule(self, schedule):
        # Save the aircraft arrival schedule for the scheduler
        self.scheduler.flight_schedule = schedule
        self.scheduler.vertiport_manager = self.vertiport_manager

        
    def convert_schedule_columns_to_ms(self, aircraft_arrival_schedule: pd.DataFrame):
        """
        Convert the columns of the aircraft arrival schedule to milliseconds.
        :param aircraft_arrival_schedule:
        :return:
        """
        # Convert the columns to milliseconds.
        aircraft_arrival_schedule['aircraft_arrival_time'] = sec_to_ms(aircraft_arrival_schedule['aircraft_arrival_time'])
        aircraft_arrival_schedule['aircraft_pushback_time'] = sec_to_ms(aircraft_arrival_schedule['aircraft_pushback_time'])
        return aircraft_arrival_schedule

    def create_aircraft_arrival(self):
        # Create aircraft arrival process.
        aircraft_arrival_schedule = self.setup_aircraft_arrival()
        
        for tail_number in aircraft_arrival_schedule.tail_number:
            # Fields to retrieve for each aircraft.
            fields = ['aircraft_pushback_time', 'interarrival_time', 'soc', 'speed', 
                    'origin_vertiport_id', 'destination_vertiport_id', 'passengers_onboard', 'location',
                    'serviced_time_at_the_location', 'priority']

            # Create a dictionary to store the retrieved values.
            aircraft_data = {}

            for field in fields:
                # Get the value of the field for the aircraft.
                aircraft_data[field] = aircraft_arrival_schedule.loc[
                    aircraft_arrival_schedule.tail_number == tail_number, field].values[0]

            yield self.env.timeout(aircraft_data['interarrival_time'])

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
                                            departure_time=aircraft_data['aircraft_pushback_time'],
                                            priority=aircraft_data['priority'])
            )         
        if self.aircraft_arrival_schedule_file_path is not None:
            self.env.process(self.scheduler.initiate_fixed_schedule_from_file()) 


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