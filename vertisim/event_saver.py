from collections import defaultdict
from utils.helpers import timestamp_to_datetime
from utils.units import ms_to_sec
from typing import Dict, Any, Union


class EventSaver:
    """
    eventSaver saves events both for analysis and visualization purposes.
    """

    def __init__(self, env, vertiports, sim_start_timestamp, sim_params, node_locations):
        self.env = env
        self.vertiports = vertiports
        self.sim_start_timestamp = sim_start_timestamp
        self.sim_params = sim_params
        self.node_locations = node_locations
        self.aircraft_agent_trajectory = defaultdict(dict)
        self.passenger_agent_trajectory = defaultdict(dict)
        self.flight_schedule = defaultdict(dict)
        self.passenger_consolidation_time = defaultdict(lambda: defaultdict(dict))
        self.aircraft_allocation_time = defaultdict(dict)
        self.aircraft_arrival_queue_count = defaultdict(dict)
        self.passenger_departure_queue_count = defaultdict(dict)
        self.aircraft_departure_queue_count = defaultdict(dict)
        self.passenger_waiting_time = defaultdict(dict)
        self.passenger_transfer_time = defaultdict(dict)
        self.passenger_departure_queue_waiting_time = defaultdict(dict)
        self.aircraft_holding_time = defaultdict(dict)
        self.aircraft_idle_time_tracker = defaultdict(dict)
        self.aircraft_charging_times = defaultdict(dict)
        self.aircraft_taxi_times = defaultdict(dict)
        self.fato_usage_tracker = defaultdict(dict)
        self.flight_time_tracker = defaultdict(dict)
        self.flight_count_tracker = defaultdict(int)
        self.load_factor_tracker = defaultdict(list)
        self.passenger_count_tracker = defaultdict(int)
        self.passenger_time_tracker = defaultdict(dict)
        for vertiport_id, _ in self.vertiports.items():
            self.aircraft_arrival_queue_count[vertiport_id][self.sim_start_timestamp] = 0
            self.passenger_departure_queue_count[vertiport_id][self.sim_start_timestamp] = 0
            self.aircraft_departure_queue_count[vertiport_id][self.sim_start_timestamp] = 0
            self.fato_usage_tracker[vertiport_id][self.sim_start_timestamp] = 0
            self.flight_count_tracker[vertiport_id] = 0
            self.passenger_count_tracker[vertiport_id] = 0
            self.passenger_time_tracker[vertiport_id][self.sim_start_timestamp] = 0

    def update_flight_tracker(self, vertiport_id):
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.flight_time_tracker[vertiport_id][time] = 1
        self.flight_count_tracker[vertiport_id] += 1

    def update_load_factor_tracker(self, vertiport_id, load_factor):
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.load_factor_tracker[vertiport_id].append(load_factor)
        self.passenger_count_tracker[vertiport_id] += load_factor
        self.passenger_time_tracker[vertiport_id][time] = load_factor
    
    def update_fato_usage_tracker(self, vertiport_id, fato_usage):
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='passenger')
        # self.fato_usage_tracker[time]['fato_id'] = fato_id
        # Get the last value from the dictionary and add the queue_update to it
        last_value = list(self.fato_usage_tracker[vertiport_id].values())[-1]
        self.fato_usage_tracker[vertiport_id][time] = last_value + fato_usage

    def save_passenger_group_consolidation_time(self, vertiport_id, passenger_ids, wr_number, consolidation_time):
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='passenger')
        self.passenger_consolidation_time[vertiport_id][time]['passenger_ids'] = passenger_ids
        self.passenger_consolidation_time[vertiport_id][time]['wr_number'] = wr_number
        self.passenger_consolidation_time[vertiport_id][time]['consolidation_time'] = consolidation_time
    
    def save_aircraft_allocation_time(self, vertiport_id, tail_number, allocation_time):
        self.aircraft_allocation_time[vertiport_id][tail_number] = allocation_time

    def save_passenger_waiting_time(self, vertiport_id: Any, passenger_id: Any, waiting_time: float) -> None:
        self.passenger_waiting_time[vertiport_id][passenger_id] = waiting_time

    def save_passenger_transfer_time(self, vertiport_id, passenger_id, transfer_time):
        self.passenger_transfer_time[vertiport_id][passenger_id] = transfer_time

    def save_passenger_departure_queue_waiting_time(self, vertiport_id, passenger_id, boarding_time):
        self.passenger_departure_queue_waiting_time[vertiport_id][passenger_id] = self.env.now - boarding_time

    def update_passenger_departure_queue_counter(self, vertiport_id, queue_update: int) -> None:
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='passenger')
        # Get the last value from the dictionary and add the queue_update to it
        last_value = list(self.passenger_departure_queue_count[vertiport_id].values())[-1]
        self.passenger_departure_queue_count[vertiport_id][time] = last_value + queue_update

    def update_aircraft_arrival_queue_counter(self, vertiport_id: Any, queue_update: int) -> None:
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        # Get the last value from the dictionary and add the queue_update to it
        last_value = list(self.aircraft_arrival_queue_count[vertiport_id].values())[-1]
        self.aircraft_arrival_queue_count[vertiport_id][time] = last_value + queue_update

    def update_aircraft_departure_queue_counter(self, vertiport_id, queue_update: int) -> None:
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        # Get the last value from the dictionary and add the queue_update to it
        last_value = list(self.aircraft_departure_queue_count[vertiport_id].values())[-1]
        self.aircraft_departure_queue_count[vertiport_id][time] = last_value + queue_update

    def save_aircraft_holding_time(self, vertiport_id, agent_id, waiting_time):
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        self.aircraft_holding_time[vertiport_id][time] =  waiting_time

    def save_aircraft_charging_time(self, vertiport_id, aircraft_id, charging_time):
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)        
        self.aircraft_charging_times[vertiport_id][time] = charging_time

    def save_aircraft_taxi_time(self, vertiport_id, aircraft_id, taxi_time):
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)        
        self.aircraft_taxi_times[vertiport_id][time] = taxi_time
    
    def save_aircraft_idle_time(self, vertiport_id: Any, agent_id: int, charging_end_time: int) -> None:
        """
        Saves the aircraft idle time
        :param origin_vertiport_id: Origin vertiport id
        :param aircraft_id: Aircraft tail number
        :param charging_end_time: Time when the aircraft is done charging
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                    sim_time=self.env.now)
        charging_end_time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                                sim_time=charging_end_time)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.aircraft_idle_time_tracker[vertiport_id][time] = time - charging_end_time


    def save_agent_state(self,
                         agent: object,
                         agent_type: str,
                         event: str = None) -> None:
        """
        Saves the agent state
        :param agent:
        :param agent_type:
        :param event:
        """          
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type=agent_type)
            if agent_type == 'aircraft':
                self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent.tail_number}'
                self.aircraft_agent_trajectory[time]['location'] = agent.location
                self.aircraft_agent_trajectory[time]['speed'] = agent.speed
                self.aircraft_agent_trajectory[time]['soc'] = agent.soc
                self.aircraft_agent_trajectory[time]['priority'] = agent.priority
                self.aircraft_agent_trajectory[time]['event'] = event
                self.aircraft_agent_trajectory[time]['latitude'] = self.node_locations[agent.location][0]
                self.aircraft_agent_trajectory[time]['longitude'] = self.node_locations[agent.location][1]  
                self.aircraft_agent_trajectory[time]['altitude'] = self.node_locations[agent.location][2]                         
            elif agent_type == 'passenger':
                self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent.passenger_id}'
                self.passenger_agent_trajectory[time]['latitude'] = self.node_locations[agent.location][0]
                self.passenger_agent_trajectory[time]['longitude'] = self.node_locations[agent.location][1]
                self.passenger_agent_trajectory[time]['altitude'] = self.node_locations[agent.location][2]
                self.passenger_agent_trajectory[time]['location'] = agent.location
                self.passenger_agent_trajectory[time]['event'] = event
            else:
                raise ValueError(f'Agent type {agent_type} is not supported')


    def save_flight_info(self, 
                         origin_vertiport_id: Any, 
                         destination_vertiport_id: Any,
                         tail_number: int, 
                         aircraft_pushback_time: float,
                         passengers: list, 
                         aircraft_model: str, 
                         event_type: str):
        """
        Saves the flight information
        :param tail_number:
        :param passengers:
        :param aircraft_model:
        :param event_type:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.flight_schedule[time]['tail_number'] = f'aircraft{tail_number}'
        self.flight_schedule[time]['origin_vertiport_id'] = origin_vertiport_id
        self.flight_schedule[time]['destination_vertiport_id'] = destination_vertiport_id
        self.flight_schedule[time]['aircraft_pushback_time'] = ms_to_sec(aircraft_pushback_time)
        self.flight_schedule[time]['passengers'] = passengers
        self.flight_schedule[time]['event'] = event_type
        self.flight_schedule[time]['aircraft_model'] = aircraft_model

    def is_time_overlapping(self, time: int, agent_type: str) -> int:
        """
        eventSaver saves each event based on the time. Events might happening in parallel. So, the eventSaver might be
        overwriting events on top of each other. To prevent this, is_time_overlapping adds 1 milisecond to the
        event's time if there are any events that happened at the same time.
        """
        # TODO: Improve this function by checking the last few elements of the trajectory dictionary
        if agent_type == 'aircraft':
            if len(self.aircraft_agent_trajectory) == 0:
                return time
            if time not in list(self.aircraft_agent_trajectory.keys()):
                return time
            time += 1  # add 1 milisecond
            return self.is_time_overlapping(time=time, agent_type=agent_type)
        elif agent_type == 'passenger':
            if len(self.passenger_agent_trajectory) == 0:
                return time
            if time not in list(self.passenger_agent_trajectory.keys()):
                return time
            time += 1
            return self.is_time_overlapping(time=time, agent_type=agent_type)
        else:
            raise ValueError('agent_type must be either aircraft or passenger')
