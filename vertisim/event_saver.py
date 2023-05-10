from collections import defaultdict
from utils.helpers import timestamp_to_datetime
from typing import Dict, Any, Union


class EventSaver:
    """
    eventSaver saves events both for analysis and visualization (unfolded.ai). unfolded.ai requires lats and longs
    to visualize points.
    Methods used to save events:
    1. save_agent_creation_time: saves the time when an agent is created
    2. save_pre_landing_info: saves the time when an aircraft is at the final approach fix
    3. save_landing_info: saves the time when an aircraft start landing process
    4. save_landing_time: saves the time when an aircraft lands at a fato
    5. save_parking_info: saves the time when an aircraft parks at a parking pad
    6. save_fatto_arrival_info: saves the time when a aircraft arrives at a fato after taxi
    7. save_take_off_info: saves the time when an aircraft takes off from a fato
    8. save_departure_fix_info: saves the time when an aircraft is at the departure fix
    9. save_taxi_location_time_info: saves the time when an aircraft is at the taxi nodes
    10. save_charging_start_time: saves the time when an aircraft starts charging
    11. save_charging_end_time: saves the time when an aircraft ends charging
    12. save_turnaround_info: saves the time when an aircraft ready to depart
    13. save_pushback_info: saves the time when an aircraft starts pushback
    14. save_passenger_vertiport_entrance_arrival_time: saves the time when a passenger arrives at the vertiport entrance
    15. save_passenger_security_check_finish_time: saves the time when a passenger finishes security check
    16. save_passenger_waiting_room_arrival_time: saves the time when a passenger arrives at the waiting room
    17. save_passenger_waiting_room_departure_time: saves the time when a passenger departs from the waiting room
    18. save_passenger_boarding_gate_arrival_time: saves the time when a passenger arrives at the boarding gate
    19. save_passenger_boarding_gate_departure_time: saves the time when a passenger departs from the boarding gate
    20. save_passenger_boarding_finish_time: saves the time when a passenger finishes boarding
    """

    def __init__(self, env, vertiports, sim_start_timestamp, sim_params):
        self.env = env
        self.vertiports = vertiports
        self.sim_start_timestamp = sim_start_timestamp
        self.sim_params = sim_params
        self.aircraft_agent_trajectory = defaultdict(dict)
        self.passenger_agent_trajectory = defaultdict(dict)
        self.flight_schedule = defaultdict(dict)
        self.passenger_consolidation_time = defaultdict(lambda: defaultdict(dict))
        self.aircraft_arrival_queue_count = defaultdict(dict)
        self.passenger_departure_queue_count = defaultdict(dict)
        self.aircraft_departure_queue_count = defaultdict(dict)
        self.passenger_waiting_time = defaultdict(dict)
        self.passenger_transfer_time = defaultdict(dict)
        self.passenger_departure_queue_waiting_time = defaultdict(dict)
        self.aircraft_arrival_queue_waiting_time = defaultdict(dict)
        self.aircraft_idle_time_tracker = defaultdict(dict)
        self.aircraft_charging_times = defaultdict(dict)
        self.aircraft_taxi_times = defaultdict(dict)
        self.fato_usage_tracker = defaultdict(dict)
        for vertiport_id, _ in self.vertiports.items():
            self.aircraft_arrival_queue_count[vertiport_id][self.sim_start_timestamp] = 0
            self.passenger_departure_queue_count[vertiport_id][self.sim_start_timestamp] = 0
            self.aircraft_departure_queue_count[vertiport_id][self.sim_start_timestamp] = 0
            self.fato_usage_tracker[vertiport_id][self.sim_start_timestamp] = 0

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

    def save_aircraft_arrival_queue_waiting_time(self, vertiport_id, agent_id, waiting_time):
        self.aircraft_arrival_queue_waiting_time[vertiport_id][agent_id] =  waiting_time

    def save_aircraft_charging_time(self, vertiport_id, aircraft_id, charging_time):
        self.aircraft_charging_times[vertiport_id][aircraft_id] = charging_time

    def save_aircraft_taxi_time(self, vertiport_id, aircraft_id, taxi_time):
        self.aircraft_taxi_times[vertiport_id][aircraft_id] = taxi_time
    
    def save_aircraft_idle_time(self, vertiport_id: Any, agent_id: int, charging_end_time: int) -> None:
        """
        Saves the aircraft idle time
        :param origin_vertiport_id: Origin vertiport id
        :param aircraft_id: Aircraft tail number
        :param aircraft_model: Aircraft model
        :param charging_end_time: Time when the aircraft is done charging
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                    sim_time=self.env.now)
        charging_end_time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                                sim_time=charging_end_time)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.aircraft_idle_time_tracker[vertiport_id][agent_id] = time - charging_end_time

    def save_agent_creation_time(self, 
                                 agent_id: int,
                                 agent_type: str,
                                 vertiport_id: Any,
                                 aircraft_model: str = None) -> None:
        """
        Saves the time when an agent is created
        :param aircraft_model:
        :param agent_id:
        :param agent_type:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type=agent_type)
            if agent_type == 'aircraft':
                self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
                # TODO: This is a hack. Need to fix this. The approach fix is not always the first one
                approach_fix_lat_lng = self.vertiports[vertiport_id].vertiport_layout.approach_fix_lat_lng.iloc[0]
                self.aircraft_agent_trajectory[time]['latitude'] = approach_fix_lat_lng.approach_fix_lat
                self.aircraft_agent_trajectory[time]['longitude'] = approach_fix_lat_lng.approach_fix_lng
                self.aircraft_agent_trajectory[time]['location'] = 'created_in_voa'
                self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
            elif agent_type == 'passenger':
                self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
                self.passenger_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.vert_door_lat_lngs.loc['ENTRANCE']['vert_door_lat']
                self.passenger_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.vert_door_lat_lngs.loc['ENTRANCE']['vert_door_lng']
                self.passenger_agent_trajectory[time]['location'] = 'arrived_at_vertiport'
            else:
                raise ValueError('agent_type must be either aircraft or passenger')
    #
    # def save_landing_approval_time(self, aircraft_id: int, aircraft_model: str) -> None:
    #     time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
    #                                  sim_time=self.env.now)
    #     time = self.is_time_overlapping(time=time, agent_type='aircraft')
    #     self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{aircraft_id}'
    #     self.aircraft_agent_trajectory[time]['latitude'] = 37.630085
    #     self.aircraft_agent_trajectory[time]['longitude'] = -122.371847
    #     self.aircraft_agent_trajectory[time]['location'] = 'landing_approved'
    #     self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_pre_landing_info(self, 
                              agent_id, 
                              aircraft_model: str = None,
                              vertiport_id: int = None,
                              agent_type: str = 'aircraft') -> None:
        """
        Saves the time when an aircraft is at the final approach fix
        :param aircraft_model:
        :param landing_fato_id:
        :param agent_id:
        :return:
        """
        
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type=agent_type)
            self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
            approach_fix_lat_lng = self.vertiports[vertiport_id].vertiport_layout.approach_fix_lat_lng.iloc[0]
            self.aircraft_agent_trajectory[time]['latitude'] = approach_fix_lat_lng.approach_fix_lat
            self.aircraft_agent_trajectory[time]['longitude'] = approach_fix_lat_lng.approach_fix_lng
            self.aircraft_agent_trajectory[time]['location'] = 'final_approach_fix'
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model   

    def save_landing_info(self, 
                          assigned_fato_id: str, 
                          agent_id: int, 
                          aircraft_model: str = None,
                          vertiport_id: int= None) -> None:
        """
        Saves the time when an aircraft start landing process
        :param aircraft_model:
        :param assigned_fato_id:
        :param agent_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='aircraft')
            self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
            self.aircraft_agent_trajectory[time]['latitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
            self.aircraft_agent_trajectory[time]['longitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
            self.aircraft_agent_trajectory[time]['location'] = assigned_fato_id
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_landing_time(self, 
                          assigned_fato_id: str, 
                          agent_id: int, 
                          aircraft_model: str = None,
                          vertiport_id:int = None) -> None:
        """
        Saves the time when an aircraft lands at a fato
        :param aircraft_model:
        :param assigned_fato_id:
        :param agent_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='aircraft')
            self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
            self.aircraft_agent_trajectory[time]['latitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
            self.aircraft_agent_trajectory[time]['longitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
            self.aircraft_agent_trajectory[time]['location'] = 'landed'
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_parking_info(self, 
                          parking_pad_id: str, 
                          agent_id: int, 
                          aircraft_model: str = None,
                          vertiport_id: int = None) -> None:
        """
        Saves the time when an aircraft is parked at a parking pad.
        :param aircraft_model:
        :param parking_pad_id:
        :param agent_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='aircraft')
            self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
            self.aircraft_agent_trajectory[time]['location'] = 'parked'
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model            
            if self.vertiports[vertiport_id].vertiport_layout.num_parking_pad == 0:
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[parking_pad_id]['fato_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[parking_pad_id]['fato_lng']
            else:
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[parking_pad_id]['parking_pad_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[parking_pad_id]['parking_pad_lng']

    def save_fato_arrival_info(self, 
                               assigned_fato_id: str, 
                               agent_id: int, 
                               agent_type: str,
                               aircraft_model: str = None,
                               vertiport_id: int = None) -> None:
        """
        Saves the time when an aircraft or passenger arrives at a fato
        :param aircraft_model:
        :param assigned_fato_id:
        :param agent_id:
        :param agent_type:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type=agent_type)
            if agent_type == 'aircraft':
                self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
                self.aircraft_agent_trajectory[time]['location'] = assigned_fato_id
                self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
            elif agent_type == 'passenger':
                self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
                self.passenger_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
                self.passenger_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
                self.passenger_agent_trajectory[time]['location'] = assigned_fato_id
            else:
                raise ValueError('agent_type must be either aircraft or passenger')

    def save_take_off_info(self, 
                           assigned_fato_id: str, 
                           agent_id: int, 
                           agent_type: str,
                           aircraft_model: str = None,
                           vertiport_id: int = None) -> None:
        """
        Saves the time when an aircraft takes off from a fato
        :param aircraft_model:
        :param assigned_fato_id:
        :param agent_id:
        :param agent_type:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type=agent_type)
            if agent_type == 'aircraft':
                self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
                self.aircraft_agent_trajectory[time]['location'] = 'take_off'
                self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
            elif agent_type == 'passenger':
                self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
                self.passenger_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
                self.passenger_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
                self.passenger_agent_trajectory[time]['location'] = 'take_off'
            else:
                raise ValueError('agent_type must be either aircraft or passenger')

    def save_departure_fix_info(self, 
                                take_off_fato_id: str, 
                                agent_id: int, 
                                agent_type: str, 
                                aircraft_model: str = None,
                                vertiport_id:int = None) -> None:
        """
        Saves the time when an aircraft arrives at the departure fix
        :param aircraft_model:
        :param take_off_fato_id:
        :param agent_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='aircraft')
            if agent_type == 'aircraft':
                self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
                departure_fix_lat_lng = self.vertiports[vertiport_id].vertiport_layout.departure_fix_lat_lng[
                    self.vertiports[vertiport_id].vertiport_layout.departure_fix_lat_lng.fato_nodes == take_off_fato_id
                    ]
                self.aircraft_agent_trajectory[time]['latitude'] = departure_fix_lat_lng.departure_fix_lat.values[0]
                self.aircraft_agent_trajectory[time]['longitude'] = departure_fix_lat_lng.departure_fix_lng.values[0]
                self.aircraft_agent_trajectory[time]['location'] = 'departure_fix'
                self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
            elif agent_type == 'passenger':
                self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
                departure_fix_lat_lng = self.vertiports[vertiport_id].vertiport_layout.departure_fix_lat_lng[
                    self.vertiports[vertiport_id].vertiport_layout.departure_fix_lat_lng.fato_nodes == take_off_fato_id
                    ]
                self.passenger_agent_trajectory[time]['latitude'] = departure_fix_lat_lng.departure_fix_lat.values[0]
                self.passenger_agent_trajectory[time]['longitude'] = departure_fix_lat_lng.departure_fix_lng.values[0]
                self.passenger_agent_trajectory[time]['location'] = 'departure_fix'
            else:
                raise ValueError('agent_type must be either aircraft or passenger')

    def save_airspace_location_time_info(self, 
                                         agent_id: int = None,
                                         agent_type: str = 'aircraft',
                                         aircraft_model: str = None,
                                         waypoint_lat_lng: tuple = None,
                                         waypoint_id: str = None) -> None:
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type=agent_type)        
            self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
            self.aircraft_agent_trajectory[time]['latitude'] = waypoint_lat_lng[0]
            self.aircraft_agent_trajectory[time]['longitude'] = waypoint_lat_lng[1]
            self.aircraft_agent_trajectory[time]['location'] = waypoint_id
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_taxi_location_time_info(self, 
                                    node: str, 
                                    agent_id: int, 
                                    agent_type: str, 
                                    aircraft_model: str = None,
                                    vertiport_id: int = None) -> None:
        """
        Saves the time when an aircraft or passenger arrives at a node
        :param aircraft_model:
        :param node:
        :param agent_id:
        :param agent_type:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type=agent_type)
            if agent_type == 'aircraft':
                self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.inters_lat_lngs.loc[node]['inters_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.inters_lat_lngs.loc[node]['inters_lng']
                self.aircraft_agent_trajectory[time]['location'] = node
                self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
            elif agent_type == 'passenger':
                self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
                self.passenger_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.inters_lat_lngs.loc[node]['inters_lat']
                self.passenger_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.inters_lat_lngs.loc[node]['inters_lng']
                self.passenger_agent_trajectory[time]['location'] = node
            else:
                raise ValueError('agent_type must be either aircraft or passenger')

    def save_charging_start_time(self, 
                                 charging_location: str, 
                                 agent_id: int, 
                                 event='charging_started',
                                 aircraft_model: str = None,
                                 vertiport_id: int = None) -> None:
        """
        Saves the time when an aircraft starts charging
        :param aircraft_model:
        :param charging_location:
        :param agent_id:
        :param event:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='aircraft')
            self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
            self.aircraft_agent_trajectory[time]['location'] = event
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
            if self.vertiports[vertiport_id].vertiport_layout.num_parking_pad == 0:
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[charging_location]['fato_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[charging_location]['fato_lng']  
            else:          
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lng']

    def save_charging_finish_time(self, 
                                  charging_location: str, 
                                  agent_id: int, 
                                  event='charging_finished',
                                  aircraft_model: str = None,
                                  vertiport_id: int = None) -> None:
        """
        Saves the time when an aircraft finishes charging
        :param aircraft_model:
        :param charging_location:
        :param agent_id:
        :param event:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='aircraft')
            self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
            self.aircraft_agent_trajectory[time]['location'] = event
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model            
            if self.vertiports[vertiport_id].vertiport_layout.num_parking_pad == 0:
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[charging_location]['fato_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[charging_location]['fato_lng']  
            else:            
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lng']

    def save_aircraft_allocation_time(self,
                                      vertiport_id: Any,
                                      parking_pad_id: str,
                                      agent_id: int,
                                      aircraft_model: str = None,
                                      agent_type: str = 'aircraft') -> None:
        """
        Saves the time when an aircraft finishes charging
        :param agent_type:
        :param aircraft_model:
        :param agent_id:
        :param parking_pad_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='aircraft')
            self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
            self.aircraft_agent_trajectory[time]['location'] = 'parked'
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model            
            if self.vertiports[vertiport_id].vertiport_layout.num_parking_pad == 0:
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[parking_pad_id]['fato_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[parking_pad_id]['fato_lng']  
            else:            
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[parking_pad_id]['parking_pad_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[parking_pad_id]['parking_pad_lng']

    def save_turnaround_info(self, 
                             charging_location: str, 
                             agent_id: int, 
                             agent_type: str,
                             aircraft_model: str = None,
                             vertiport_id: int = None) -> None:
        """
        Saves the time when an aircraft is ready for pushback
        :param aircraft_model:
        :param charging_location:
        :param agent_id:
        :param agent_type:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type=agent_type)
            if agent_type == 'aircraft':
                self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
                self.aircraft_agent_trajectory[time]['location'] = 'ready_for_leaving'
                self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model                
                if self.vertiports[vertiport_id].vertiport_layout.num_parking_pad == 0:
                    self.aircraft_agent_trajectory[time]['latitude'] = \
                        self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[charging_location]['fato_lat']
                    self.aircraft_agent_trajectory[time]['longitude'] = \
                        self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[charging_location]['fato_lng']  
                else:                
                    self.aircraft_agent_trajectory[time]['latitude'] = \
                        self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lat']
                    self.aircraft_agent_trajectory[time]['longitude'] = \
                        self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lng']
            elif agent_type == 'passenger':
                self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'  
                self.passenger_agent_trajectory[time]['location'] = 'ready_for_leaving'
                if self.vertiports[vertiport_id].vertiport_layout.num_parking_pad == 0:
                    self.passenger_agent_trajectory[time]['latitude'] = \
                        self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[charging_location]['fato_lat']
                    self.passenger_agent_trajectory[time]['longitude'] = \
                        self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[charging_location]['fato_lng']
                else:                              
                    self.passenger_agent_trajectory[time]['latitude'] = \
                        self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lat']
                    self.passenger_agent_trajectory[time]['longitude'] = \
                        self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lng']


    def save_pushback_info(self, 
                           pushback_location: str, 
                           agent_id: int, 
                           aircraft_model: str = None,
                           vertiport_id: int = None) -> None:
        """
        Saves the time when an aircraft starts pushback
        :param aircraft_model:
        :param pushback_location:
        :param agent_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='aircraft')
            self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
            self.aircraft_agent_trajectory[time]['location'] = 'Pushback_time'
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model            
            if self.vertiports[vertiport_id].vertiport_layout.num_parking_pad == 0:
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[pushback_location]['fato_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[pushback_location]['fato_lng']  
            else:            
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[pushback_location]['parking_pad_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[pushback_location]['parking_pad_lng']

    def save_flight_info(self, 
                         origin_vertiport_id: Any, 
                         destination_vertiport_id: Any,
                         tail_number: int, 
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
        self.flight_schedule[time]['tail_number'] = f'aircraft_{tail_number}'
        self.flight_schedule[time]['origin_vertiport_id'] = origin_vertiport_id
        self.flight_schedule[time]['destination_vertiport_id'] = destination_vertiport_id
        self.flight_schedule[time]['passengers'] = passengers
        self.flight_schedule[time]['aircraft_model'] = aircraft_model
        self.flight_schedule[time]['event'] = event_type

    def save_passenger_vertiport_entrance_arrival_time(self, vertiport_id: Any, passenger_id: int) -> None:
        """
        Saves the time when a passenger arrives at the vertiport entrance
        :param passenger_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='passenger')
            self.passenger_agent_trajectory[time]['passenger_id'] = f'passenger{passenger_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.vert_door_lat_lngs.loc['ENTRANCE']['vert_door_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.vert_door_lat_lngs.loc['ENTRANCE']['vert_door_lng']
            self.passenger_agent_trajectory[time]['location'] = 'vertiport_entrance'

    def save_passenger_security_check_finish_time(self, vertiport_id: Any, passenger_id: int) -> None:
        """
        Saves the time when a passenger finishes security check
        :param passenger_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='passenger')
            self.passenger_agent_trajectory[time]['passenger_id'] = f'passenger{passenger_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.vert_door_lat_lngs.loc['ENTRANCE']['vert_door_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.vert_door_lat_lngs.loc['ENTRANCE']['vert_door_lng']
            self.passenger_agent_trajectory[time]['location'] = 'security_check_finish'

    def save_passenger_waiting_room_arrival_time(self, vertiport_id, passenger_id: int, waiting_room_id: str):
        """
        Saves the time when a passenger arrives at the waiting room
        :param passenger_id:
        :param waiting_room_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='passenger')
            self.passenger_agent_trajectory[time]['passenger_id'] = f'passenger{passenger_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.waiting_room_lat_lngs.loc['ROOM']['waiting_room_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.waiting_room_lat_lngs.loc['ROOM']['waiting_room_lng']
            self.passenger_agent_trajectory[time]['location'] = f'waiting_room_{waiting_room_id}'

    def save_passenger_group_completion_time(self, vertiport_id: Any, passenger_id: int, agent_type: str = 'passenger'):
        """
        Saves the time when there are enough passengers to create a flight
        :param passenger_id:
        :param agent_type:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type=agent_type)
            self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{passenger_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.waiting_room_lat_lngs.loc['ROOM']['waiting_room_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.waiting_room_lat_lngs.loc['ROOM']['waiting_room_lng']
            self.passenger_agent_trajectory[time]['location'] = 'passenger_group_completed'

    def save_passenger_flight_assignment_time(self, vertiport_id: Any, passenger_id: int, agent_type: str = 'passenger'):
        """
        Saves the time when a passenger is assigned to a flight
        :param passenger_id:
        :param agent_type:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type=agent_type)
            self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{passenger_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.waiting_room_lat_lngs.loc['ROOM']['waiting_room_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.waiting_room_lat_lngs.loc['ROOM']['waiting_room_lng']
            self.passenger_agent_trajectory[time]['location'] = 'flight_assignment'

    def save_aircraft_flight_assignment_time(self, 
                                             vertiport_id: Any, 
                                             parking_pad_id: str,
                                             agent_id: int, 
                                             agent_type: str = 'aircraft',
                                             aircraft_model: str = None) -> None:
        """
        Saves the time when an aircraft is assigned to a flight
        :param agent_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type=agent_type)
            self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
            self.aircraft_agent_trajectory[time]['location'] = 'flight_assignment'
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model            
            if self.vertiports[vertiport_id].vertiport_layout.num_parking_pad == 0:
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[parking_pad_id]['fato_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[parking_pad_id]['fato_lng']  
            else:            
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[parking_pad_id]['parking_pad_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[parking_pad_id]['parking_pad_lng']

    def save_passenger_waiting_room_departure_time(self,
                                                   agent_id: int,
                                                   vertiport_id: Any,
                                                   waiting_room_id: str,
                                                   agent_type: str = 'passenger'):
        """
        Saves the time when a passenger departs from the waiting room
        :param agent_type:
        :param passenger_id:
        :param waiting_room_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='passenger')
            self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.waiting_room_lat_lngs.loc['ROOM']['waiting_room_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.waiting_room_lat_lngs.loc['ROOM']['waiting_room_lng']
            self.passenger_agent_trajectory[time]['location'] = f'waiting_room_{waiting_room_id}_departure'

    def save_passenger_boarding_gate_arrival_time(self, vertiport_id: Any, agent_id: int, agent_type: str = 'passenger') -> None:
        """
        Saves the time when a passenger arrives at the boarding gate
        :param vertiport_id:
        :param agent_type:
        :param agent_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='passenger')
            self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.boarding_gate_lat_lngs.loc['GATE']['boarding_gate_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.boarding_gate_lat_lngs.loc['ROOM']['boarding_gate_lng']
            self.passenger_agent_trajectory[time]['location'] = 'boarding_gate'

    def save_passenger_boarding_gate_departure_time(self, vertiport_id: Any, passenger_id: int) -> None:
        """
        Save passenger boarding gate departure time
        :param vertiport_id:
        :param passenger_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='passenger')
            self.passenger_agent_trajectory[time]['passenger_id'] = f'passenger{passenger_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.boarding_gate_lat_lngs.loc['GATE']['boarding_gate_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiports[vertiport_id].vertiport_layout.boarding_gate_lat_lngs.loc['ROOM']['boarding_gate_lng']
            self.passenger_agent_trajectory[time]['location'] = 'boarding_gate_exit'

    def save_passenger_boarding_finish_time(self, 
                                            passenger_id: int,
                                            aircraft: int,
                                            vertiport_id: int):
        """
        Save passenger boarding finish time
        :param aircraft:
        :param passenger_id:
        :return:
        """
        if self.sim_params['save_trajectories']:
            time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                        sim_time=self.env.now)
            time = self.is_time_overlapping(time=time, agent_type='passenger')
            self.passenger_agent_trajectory[time]['passenger_id'] = f'passenger{passenger_id}'
            self.passenger_agent_trajectory[time]['location'] = f'boarding_finish_tail_number_{aircraft.tail_number}'
            if self.vertiports[vertiport_id].vertiport_layout.num_parking_pad == 0:
                self.aircraft_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[aircraft.parking_space_id]['fato_lat']
                self.aircraft_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.fato_lat_lngs.loc[aircraft.parking_space_id]['fato_lng']
            else:                
                self.passenger_agent_trajectory[time]['latitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[aircraft.parking_space_id]['parking_pad_lat']
                self.passenger_agent_trajectory[time]['longitude'] = \
                    self.vertiports[vertiport_id].vertiport_layout.park_lat_lngs.loc[aircraft.parking_space_id]['parking_pad_lng']

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
