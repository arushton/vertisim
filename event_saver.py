from collections import defaultdict
from utils.helpers import timestamp_to_datetime


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
    9. save_location_time_info: saves the time when an aircraft is at the taxi nodes
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

    def __init__(self, env, vertiport_layout, sim_start_timestamp):
        self.env = env
        self.vertiport_layout = vertiport_layout
        self.sim_start_timestamp = sim_start_timestamp
        self.aircraft_agent_trajectory = defaultdict(dict)
        self.passenger_agent_trajectory = defaultdict(dict)

    def save_agent_creation_time(self, agent_id: int,
                                 agent_type: str,
                                 aircraft_model: str = None) -> None:
        """
        Saves the time when an agent is created
        :param aircraft_model:
        :param agent_id:
        :param agent_type:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type=agent_type)
        if agent_type == 'aircraft':
            self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
            self.aircraft_agent_trajectory[time]['latitude'] = 0
            self.aircraft_agent_trajectory[time]['longitude'] = 0
            self.aircraft_agent_trajectory[time]['location'] = 'created_in_voa'
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
        elif agent_type == 'passenger':
            self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
            self.passenger_agent_trajectory[time]['latitude'] = 0
            self.passenger_agent_trajectory[time]['longitude'] = 0
            self.passenger_agent_trajectory[time]['location'] = 'arrived_at_vertiport'
        else:
            raise ValueError('agent_type must be either aircraft or passenger')

    def save_pre_landing_info(self, landing_fato_id, agent_id, aircraft_model: str = None):
        """
        Saves the time when an aircraft is at the final approach fix
        :param aircraft_model:
        :param landing_fato_id:
        :param agent_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'

        approach_fix_lat_lng = self.vertiport_layout.approach_fix_lat_lng[
            self.vertiport_layout.approach_fix_lat_lng.fato_nodes == landing_fato_id
            ]
        self.aircraft_agent_trajectory[time]['latitude'] = approach_fix_lat_lng.approach_fix_lat.values[0]
        self.aircraft_agent_trajectory[time]['longitude'] = approach_fix_lat_lng.approach_fix_lng.values[0]
        self.aircraft_agent_trajectory[time]['location'] = 'final_approach_fix'
        self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_landing_info(self, assigned_fato_id: str, agent_id: int, aircraft_model: str = None) -> None:
        """
        Saves the time when an aircraft start landing process
        :param aircraft_model:
        :param assigned_fato_id:
        :param agent_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
        self.aircraft_agent_trajectory[time]['latitude'] = \
            self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
        self.aircraft_agent_trajectory[time]['longitude'] = \
            self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
        self.aircraft_agent_trajectory[time]['location'] = assigned_fato_id
        self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_landing_time(self, assigned_fato_id: str, agent_id: int, aircraft_model: str = None) -> None:
        """
        Saves the time when an aircraft lands at a fato
        :param aircraft_model:
        :param assigned_fato_id:
        :param agent_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
        self.aircraft_agent_trajectory[time]['latitude'] = \
            self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
        self.aircraft_agent_trajectory[time]['longitude'] = \
            self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
        self.aircraft_agent_trajectory[time]['location'] = 'landed'
        self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_parking_info(self, parking_pad_id: str, agent_id: int, aircraft_model: str = None) -> None:
        """
        Saves the time when an aircraft is parked at a parking pad.
        :param aircraft_model:
        :param parking_pad_id:
        :param agent_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
        self.aircraft_agent_trajectory[time]['latitude'] = \
            self.vertiport_layout.park_lat_lngs.loc[parking_pad_id]['parking_pad_lat']
        self.aircraft_agent_trajectory[time]['longitude'] = \
            self.vertiport_layout.park_lat_lngs.loc[parking_pad_id]['parking_pad_lng']
        self.aircraft_agent_trajectory[time]['location'] = 'parked'
        self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_fato_arrival_info(self, assigned_fato_id: str, agent_id: int, agent_type: str,
                               aircraft_model: str = None) -> None:
        """
        Saves the time when an aircraft or passenger arrives at a fato
        :param aircraft_model:
        :param assigned_fato_id:
        :param agent_id:
        :param agent_type:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type=agent_type)
        if agent_type == 'aircraft':
            self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
            self.aircraft_agent_trajectory[time]['latitude'] = \
                self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
            self.aircraft_agent_trajectory[time]['longitude'] = \
                self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
            self.aircraft_agent_trajectory[time]['location'] = assigned_fato_id
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
        elif agent_type == 'passenger':
            self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
            self.passenger_agent_trajectory[time]['location'] = assigned_fato_id
        else:
            raise ValueError('agent_type must be either aircraft or passenger')

    def save_take_off_info(self, assigned_fato_id: str, agent_id: int, agent_type: str,
                           aircraft_model: str = None) -> None:
        """
        Saves the time when an aircraft takes off from a fato
        :param aircraft_model:
        :param assigned_fato_id:
        :param agent_id:
        :param agent_type:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type=agent_type)
        if agent_type == 'aircraft':
            self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
            self.aircraft_agent_trajectory[time]['latitude'] = \
                self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
            self.aircraft_agent_trajectory[time]['longitude'] = \
                self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
            self.aircraft_agent_trajectory[time]['location'] = 'take_off'
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
        elif agent_type == 'passenger':
            self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiport_layout.fato_lat_lngs.loc[assigned_fato_id]['fato_lng']
            self.passenger_agent_trajectory[time]['location'] = 'take_off'
        else:
            raise ValueError('agent_type must be either aircraft or passenger')

    def save_departure_fix_info(self, take_off_fato_id: str, agent_id: int, agent_type: str, aircraft_model: str = None) -> None:
        """
        Saves the time when an aircraft arrives at the departure fix
        :param aircraft_model:
        :param take_off_fato_id:
        :param agent_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        if agent_type == 'aircraft':
            self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
            departure_fix_lat_lng = self.vertiport_layout.departure_fix_lat_lng[
                self.vertiport_layout.departure_fix_lat_lng.fato_nodes == take_off_fato_id
                ]
            self.aircraft_agent_trajectory[time]['latitude'] = departure_fix_lat_lng.departure_fix_lat.values[0]
            self.aircraft_agent_trajectory[time]['longitude'] = departure_fix_lat_lng.departure_fix_lng.values[0]
            self.aircraft_agent_trajectory[time]['location'] = 'departure_fix'
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
        elif agent_type == 'passenger':
            self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
            departure_fix_lat_lng = self.vertiport_layout.departure_fix_lat_lng[
                self.vertiport_layout.departure_fix_lat_lng.fato_nodes == take_off_fato_id
                ]
            self.passenger_agent_trajectory[time]['latitude'] = departure_fix_lat_lng.departure_fix_lat.values[0]
            self.passenger_agent_trajectory[time]['longitude'] = departure_fix_lat_lng.departure_fix_lng.values[0]
            self.passenger_agent_trajectory[time]['location'] = 'departure_fix'
        else:
            raise ValueError('agent_type must be either aircraft or passenger')

    def save_location_time_info(self, node: str, agent_id: int, agent_type: str, aircraft_model: str = None) -> None:
        """
        Saves the time when an aircraft or passenger arrives at a node
        :param aircraft_model:
        :param node:
        :param agent_id:
        :param agent_type:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type=agent_type)
        if agent_type == 'aircraft':
            self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
            self.aircraft_agent_trajectory[time]['latitude'] = \
                self.vertiport_layout.inters_lat_lngs.loc[node]['inters_lat']
            self.aircraft_agent_trajectory[time]['longitude'] = \
                self.vertiport_layout.inters_lat_lngs.loc[node]['inters_lng']
            self.aircraft_agent_trajectory[time]['location'] = node
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
        elif agent_type == 'passenger':
            self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiport_layout.inters_lat_lngs.loc[node]['inters_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiport_layout.inters_lat_lngs.loc[node]['inters_lng']
            self.passenger_agent_trajectory[time]['location'] = node
        else:
            raise ValueError('agent_type must be either aircraft or passenger')

    def save_charging_start_time(self, charging_location: str, agent_id: int, event='charging_started',
                                 aircraft_model: str = None) -> None:
        """
        Saves the time when an aircraft starts charging
        :param aircraft_model:
        :param charging_location:
        :param agent_id:
        :param event:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
        self.aircraft_agent_trajectory[time]['latitude'] = \
            self.vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lat']
        self.aircraft_agent_trajectory[time]['longitude'] = \
            self.vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lng']
        self.aircraft_agent_trajectory[time]['location'] = event
        self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_charging_finish_time(self, charging_location: str, agent_id: int, event='charging_finished',
                                  aircraft_model: str = None):
        """
        Saves the time when an aircraft finishes charging
        :param aircraft_model:
        :param charging_location:
        :param agent_id:
        :param event:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
        self.aircraft_agent_trajectory[time]['latitude'] = \
            self.vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lat']
        self.aircraft_agent_trajectory[time]['longitude'] = \
            self.vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lng']
        self.aircraft_agent_trajectory[time]['location'] = event
        self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_aircraft_allocation_time(self,
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
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
        self.aircraft_agent_trajectory[time]['latitude'] = \
            self.vertiport_layout.park_lat_lngs.loc[parking_pad_id]['parking_pad_lat']
        self.aircraft_agent_trajectory[time]['longitude'] = \
            self.vertiport_layout.park_lat_lngs.loc[parking_pad_id]['parking_pad_lng']
        self.aircraft_agent_trajectory[time]['location'] = 'parked'
        self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_turnaround_info(self, charging_location: str, agent_id: int, agent_type: str,
                             aircraft_model: str = None) -> None:
        """
        Saves the time when an aircraft is ready for pushback
        :param aircraft_model:
        :param charging_location:
        :param agent_id:
        :param agent_type:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type=agent_type)
        if agent_type == 'aircraft':
            self.aircraft_agent_trajectory[time]['tail_number'] = f'{agent_type}{agent_id}'
            self.aircraft_agent_trajectory[time]['latitude'] = \
                self.vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lat']
            self.aircraft_agent_trajectory[time]['longitude'] = \
                self.vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lng']
            self.aircraft_agent_trajectory[time]['location'] = 'ready_for_leaving'
            self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model
        elif agent_type == 'passenger':
            self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
            self.passenger_agent_trajectory[time]['latitude'] = \
                self.vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lat']
            self.passenger_agent_trajectory[time]['longitude'] = \
                self.vertiport_layout.park_lat_lngs.loc[charging_location]['parking_pad_lng']
            self.passenger_agent_trajectory[time]['location'] = 'ready_for_leaving'

    def save_pushback_info(self, pushback_location: str, agent_id: int, aircraft_model: str = None) -> None:
        """
        Saves the time when an aircraft starts pushback
        :param aircraft_model:
        :param pushback_location:
        :param agent_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='aircraft')
        self.aircraft_agent_trajectory[time]['tail_number'] = f'aircraft{agent_id}'
        self.aircraft_agent_trajectory[time]['latitude'] = \
            self.vertiport_layout.park_lat_lngs.loc[pushback_location]['parking_pad_lat']
        self.aircraft_agent_trajectory[time]['longitude'] = \
            self.vertiport_layout.park_lat_lngs.loc[pushback_location]['parking_pad_lng']
        self.aircraft_agent_trajectory[time]['location'] = 'Pushback_time'
        self.aircraft_agent_trajectory[time]['aircraft_model'] = aircraft_model

    def save_passenger_vertiport_entrance_arrival_time(self, passenger_id: int) -> None:
        """
        Saves the time when a passenger arrives at the vertiport entrance
        :param passenger_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='passenger')
        self.passenger_agent_trajectory[time]['passenger_id'] = f'passenger{passenger_id}'
        self.passenger_agent_trajectory[time]['latitude'] = 0
        self.passenger_agent_trajectory[time]['longitude'] = 0
        self.passenger_agent_trajectory[time]['location'] = 'vertiport_entrance'

    def save_passenger_security_check_finish_time(self, passenger_id: int) -> None:
        """
        Saves the time when a passenger finishes security check
        :param passenger_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='passenger')
        self.passenger_agent_trajectory[time]['passenger_id'] = f'passenger{passenger_id}'
        self.passenger_agent_trajectory[time]['latitude'] = 0
        self.passenger_agent_trajectory[time]['longitude'] = 0
        self.passenger_agent_trajectory[time]['location'] = 'security_check_finish'

    def save_passenger_waiting_room_arrival_time(self, passenger_id: int, waiting_room_id: str):
        """
        Saves the time when a passenger arrives at the waiting room
        :param passenger_id:
        :param waiting_room_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='passenger')
        self.passenger_agent_trajectory[time]['passenger_id'] = f'passenger{passenger_id}'
        self.passenger_agent_trajectory[time]['latitude'] = 0
        self.passenger_agent_trajectory[time]['longitude'] = 0
        self.passenger_agent_trajectory[time]['location'] = f'waiting_room_{waiting_room_id}'

    def save_passenger_group_completion_time(self, passenger_id: int, agent_type: str = 'passenger'):
        """
        Saves the time when there are enough passengers to create a flight
        :param passenger_id:
        :param agent_type:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type=agent_type)
        self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{passenger_id}'
        self.passenger_agent_trajectory[time]['latitude'] = 0
        self.passenger_agent_trajectory[time]['longitude'] = 0
        self.passenger_agent_trajectory[time]['location'] = 'passenger_group_completed'

    def save_passenger_flight_assignment_time(self, passenger_id: int, agent_type: str = 'passenger'):
        """
        Saves the time when a passenger is assigned to a flight
        :param passenger_id:
        :param agent_type:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type=agent_type)
        self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{passenger_id}'
        self.passenger_agent_trajectory[time]['latitude'] = 0
        self.passenger_agent_trajectory[time]['longitude'] = 0
        self.passenger_agent_trajectory[time]['location'] = 'flight_assignment'

    def save_passenger_waiting_room_departure_time(self, agent_id: int,
                                                   waiting_room_id: str,
                                                   agent_type: str = 'passenger'):
        """
        Saves the time when a passenger departs from the waiting room
        :param agent_type:
        :param passenger_id:
        :param waiting_room_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='passenger')
        self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
        self.passenger_agent_trajectory[time]['latitude'] = 0
        self.passenger_agent_trajectory[time]['longitude'] = 0
        self.passenger_agent_trajectory[time]['location'] = f'waiting_room_{waiting_room_id}_departure'

    def save_passenger_boarding_gate_arrival_time(self, agent_id: int, agent_type: str = 'passenger'):
        """
        Saves the time when a passenger arrives at the boarding gate
        :param agent_type:
        :param agent_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='passenger')
        self.passenger_agent_trajectory[time]['passenger_id'] = f'{agent_type}{agent_id}'
        self.passenger_agent_trajectory[time]['latitude'] = 0
        self.passenger_agent_trajectory[time]['longitude'] = 0
        self.passenger_agent_trajectory[time]['location'] = 'boarding_gate'

    def save_passenger_boarding_gate_departure_time(self, passenger_id: int):
        """
        Save passenger boarding gate departure time
        :param passenger_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='passenger')
        self.passenger_agent_trajectory[time]['passenger_id'] = f'passenger{passenger_id}'
        self.passenger_agent_trajectory[time]['latitude'] = 0
        self.passenger_agent_trajectory[time]['longitude'] = 0
        self.passenger_agent_trajectory[time]['location'] = 'boarding_gate_exit'

    def save_passenger_boarding_finish_time(self, passenger_id: int, aircraft_id: int):
        """
        Save passenger boarding finish time
        :param aircraft_id:
        :param passenger_id:
        :return:
        """
        time = timestamp_to_datetime(sim_start_time=self.sim_start_timestamp,
                                     sim_time=self.env.now)
        time = self.is_time_overlapping(time=time, agent_type='passenger')
        self.passenger_agent_trajectory[time]['passenger_id'] = f'passenger{passenger_id}'
        self.passenger_agent_trajectory[time]['latitude'] = 0
        self.passenger_agent_trajectory[time]['longitude'] = 0
        self.passenger_agent_trajectory[time]['location'] = f'boarding_finish_tail_number_{aircraft_id}'

    def is_time_overlapping(self, time: int, agent_type: str) -> int:
        """
        eventSaver saves each event based on the time. Events might happening in parallel. So, the eventSaver might be
        overwriting events on top of each other. To prevent this, is_time_overlapping adds 1 milisecond to the
        event's time if there are any events that happened at the same time.
        """
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
