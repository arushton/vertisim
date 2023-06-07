from typing import Dict, Union, Callable, Optional, Dict, List
from utils.units import sec_to_ms, ms_to_sec
from utils.helpers import miliseconds_to_hms, seconds_to_hms, get_random_process_id
from collections import defaultdict


class Scheduler:
    def __init__(self, env: object,
                 vertiports: object,
                 vertiport_manager: object,
                 aircraft_capacity: int = None,
                 is_fixed_schedule: bool = False,
                 logger: object = None):
        self.env = env
        self.vertiports = vertiports
        self.aircraft_capacity = aircraft_capacity
        self.vertiport_manager = vertiport_manager
        self.is_fixed_schedule = is_fixed_schedule
        self.logger = logger
        self.flight_schedule = None
        self.charge_schedule = None

    def initiate_fixed_schedule_from_file(self):
        # print('Initiating fixed schedule from file.')
        for _, row in self.flight_schedule.iterrows():
            pushback_interarrival_time = row['pushback_interarrival_time']
            origin_vertiport_id = row['origin_vertiport_id']
            destination_vertiport_id = row['destination_vertiport_id']
            yield self.env.timeout(pushback_interarrival_time)

            self.logger.info(f"Pushback time: {seconds_to_hms(row['aircraft_pushback_time'])} Flight scheduled from {origin_vertiport_id}"
                             f" to {destination_vertiport_id} for SOC: {row['soc']}.")

            # Get the waiting room for the destination
            waiting_room = self.vertiports[origin_vertiport_id].waiting_room_stores[destination_vertiport_id]
            # Get the departing passengers from the waiting room
            departing_passengers = self.collect_any_departing_passengers(waiting_room)
            # print(f"Aircraft {row['tail_number']}, with soc {row['soc']} is departing with {len(departing_passengers)} passengers from {origin_vertiport_id} at {ms_to_sec(self.env.now)}.")
            # print(f"Avaible aircraft ids: {[aircraft.tail_number for aircraft in self.vertiports[origin_vertiport_id].available_aircraft_store.items]}")
            self.env.process(self.vertiport_manager.reserve_aircraft(origin_vertiport_id=origin_vertiport_id,
                                                                     destination_vertiport_id=destination_vertiport_id,
                                                                     departing_passengers=departing_passengers,
                                                                     tail_number=row['tail_number'],
                                                                     soc=row['soc']))
        
    # def initiate_charge_schedule_from_file(self):
    #     for _, row in self.charge_schedule.iterrows():
    #         yield self.env.timeout(row['charge_interarrival_time'])
    #         self.logger.info(f"Charge Initiation by Scheduler at {seconds_to_hms(row['charging_start_time'])}: At vertiport {row['vertiport_id']} from {row['init_soc']} to {row['target_soc']}.")
    #         # Get the aircraft that has the closes SOC to the init_soc
    #         aircraft = yield self.get_aircraft_with_closest_init_soc(vertiport_id=row['vertiport_id'], 
    #                                                                  init_soc=row['init_soc'])
    #         self.logger.info(f"Scheduler got aircraft {aircraft.tail_number} with init soc {aircraft.soc} and target soc: {row['target_soc']} at vertiport {row['vertiport_id']}.")
    #         aircraft.target_soc = row['target_soc']
    #         self.env.process(self.vertiport_manager.aircraft_charging_process(aircraft=aircraft))

    def initiate_charge_schedule_from_file(self):
        interarrival_time_sum = 0
        for _, row in self.charge_schedule.iterrows():
            interarrival_time_sum += row['charge_interarrival_time']
            self.env.process(self.initiate_charge_for_aircraft(row, interarrival_time_sum))

    def initiate_charge_for_aircraft(self, row, interarrival_time):
        yield self.env.timeout(interarrival_time)
        random_id = get_random_process_id()
        self.logger.info(f"|{random_id}| Charge Initiation by Scheduler at {seconds_to_hms(row['charging_start_time'])}: At vertiport {row['vertiport_id']} from {row['init_soc']} to {row['target_soc']}.")
        aircraft = yield self.get_aircraft_with_closest_init_soc(vertiport_id=row['vertiport_id'], 
                                                                init_soc=row['init_soc'],
                                                                target_soc=row['target_soc'])
        self.logger.info(f"|{random_id}| Scheduler got aircraft {aircraft.tail_number} for charging with init soc {round(aircraft.soc, 2)} and target soc: {row['target_soc']} at vertiport {row['vertiport_id']}.")
        aircraft.target_soc = row['target_soc']
        self.env.process(self.vertiport_manager.aircraft_charging_process(aircraft=aircraft))

    def check_max_waiting_time_threshold(self, max_flight_waiting_time):
        """
        Checks all of the waiting rooms. If there are passengers who are waiting
        more than max_flight_waiting_time, it creates a flight for those passengers immediately.
        """
        departing_passenger_groups = defaultdict(lambda: defaultdict(list))
        for origin, vertiport in self.vertiports.items():
            for destination, wr_store in vertiport.waiting_room_stores.items():
                num_agents_in_the_wr = len(wr_store.items)
                if num_agents_in_the_wr > 0:
                    for waiting_passenger in wr_store.items:
                        if self.env.now - waiting_passenger.waiting_room_arrival_time >= max_flight_waiting_time:
                            # Collect the passengers in the waiting rooms that are waited max_flight_waiting_time or more
                            num_departing_passengers = min(self.aircraft_capacity, num_agents_in_the_wr)
                            departing_passengers = Scheduler.collect_departing_passengers(wr_store, num_departing_passengers)
                            departing_passenger_groups[origin][destination].extend(departing_passengers)

        return departing_passenger_groups


    def check_waiting_room(self, current_waiting_room):
        """
        Checks the departing_passenger's waiting room if that reached the
        aircraft_capacity. If yes then trigger reserve_aircraft
        """
        if len(current_waiting_room.items) >= self.aircraft_capacity:
            return Scheduler.collect_departing_passengers(current_waiting_room, self.aircraft_capacity)
        else:
            return None


    def last_call_check(self, current_waiting_room, num_departing_passengers):
        """
         After allocating an aircraft, checks the waiting room again. If there are newcomers add them to the flight list
        """
        return Scheduler.collect_departing_passengers(current_waiting_room, 
                                                      self.aircraft_capacity - num_departing_passengers
                                                      )

    @staticmethod
    def collect_departing_passengers(current_waiting_room, num_departing_passengers) -> Union[None, List]:
        departing_passengers = []
        for _ in range(min(num_departing_passengers, len(current_waiting_room.items))):
            # Collect agents from the waiting room as FIFO
            departing_passengers.append(current_waiting_room.items[0])
            # Remove the agent from the current_waiting_room
            current_waiting_room.get()
        return departing_passengers
    
    def collect_any_departing_passengers(self, waiting_room):
        """
        Collects any departing passengers from the waiting room
        """
        departing_passengers = []
        for _ in range(min(self.aircraft_capacity, len(waiting_room.items))):
            # Collect agents from the waiting room as FIFO)
            departing_passengers.append(waiting_room.items[0])
            # Remove the agent from the current_waiting_room
            waiting_room.get()
        return departing_passengers

    def get_aircraft_with_closest_init_soc(self, vertiport_id, init_soc, target_soc):
        """
        Returns the aircraft that has the closes SOC to the init_soc
        """
        return self.vertiports[vertiport_id].available_aircraft_store.get(
            lambda aircraft: abs(aircraft.soc - init_soc) <= 9 and aircraft.soc < target_soc)


def noninteruptive_aircraft_assignment_strategy(current_waiting_room,
                                                mission_length,
                                                available_aircraft_store):
    """
    Check only available aircraft. Aircraft can become available after they finish their charging process.
    """
    aircraft_can_complete_mission = get_available_aircraft_can_complete_mission(current_waiting_room,
                                                                                available_aircraft_store,
                                                                                mission_length)
    if any_available_aircraft(available_aircraft_store):
        # Get the aircraft that has the least passenger_capacity. TODO: This can maximize the aircraft throughput but
        #  not the passenger throughput
        return get_min_passenger_capacity_aircraft(aircraft_can_complete_mission)
    else:
        return None


def get_min_passenger_capacity_aircraft(aircraft_can_complete_mission):
    """
    Returns the aircraft with the least passenger capacity
    """
    return min(aircraft_can_complete_mission, key=lambda x: x.passenger_capacity)


def any_available_aircraft(available_aircraft_store):
    """
    Checks if there is any available aircraft in the available aircraft store
    :return:
    """
    return len(available_aircraft_store.items) > 0


def get_available_aircraft_can_complete_mission(current_waiting_room, available_aircraft_store, mission_length):
    """
    Returns the available aircraft that can fly the mission range
    """
    aircraft_can_complete_mission = []
    for aircraft in available_aircraft_store.items:
        if len(current_waiting_room.items) >= aircraft.passenger_capacity and aircraft.max_range >= mission_length:
            aircraft_can_complete_mission.append(aircraft)
    return aircraft_can_complete_mission


    # def aircraft_assignment_strategy(self,
    #                                  current_waiting_room,
    #                                  available_aircraft_store,
    #                                  mission_length):
    #     """
    #
    #     """
    #     if not self.dynamic_assignment:
    #
    #
    #
    #     if not self.charge_interruption:
    #         return self.noninteruptive_aircraft_assignment_strategy(current_waiting_room, available_aircraft_store,
    #                                                            mission_length)
    #     else:
    #         aircraft_can_complete_mission = []

    # def get_active_aircraft_can_complete_mission(self, current_waiting_room, active_aircraft_store, mission_length):
    #     """
    #     Returns the active aircraft that can fly the mission range. NOT USED
    #     """
    #     aircraft_can_complete_mission = []
    #     for aircraft in active_aircraft_store.items:
    #         if len(current_waiting_room.items) >= aircraft.passenger_capacity and aircraft.max_range >= mission_length:
    #             aircraft_can_complete_mission.append(aircraft)
    #     return aircraft_can_complete_mission

    # def interuptive_aircraft_assignment_strategy(self, current_waiting_room, active_aircraft_store,
    #                                              available_aircraft_store, mission_length):
    #     """
    #     First check the active aircraft (aircraft under charging). If there is no active aircraft that can complete the
    #     mission, check the available aircraft. INCOMPLETE
    #     """
    #     active_aircraft_can_complete_mission = self.get_active_aircraft_can_complete_mission(current_waiting_room,
    #                                                                                     active_aircraft_store,
    #                                                                                     mission_length)
    #     if len(active_aircraft_can_complete_mission) == 0:
    #         available_aircraft_can_complete_mission = self.get_available_aircraft_can_complete_mission(current_waiting_room,
    #                                                                                         available_aircraft_store,
    #                                                                                         mission_length)
    #
    #         # Check the aircrafts' current SOC and check whether they can complete the mission
    #         for aircraft in aircraft_can_complete_mission:
    #             mission_required_energy = self.get_required_energy_for_mission(aircraft, pax, mission_length)
    #             if (env.now - aircraft.charging_start_time) >= calc_required_charge_time_from_required_energy(
    #                     mission_required_energy,
    #                     aircraft.initial_soc,
    #                     min_reserve_soc,
    #                     aircraft_battery_models[aircraft.aircraft_model])
    #
    #     if not aircraft_can_complete_mission:
    #         return noninteruptive_aircraft_assignment_strategy(current_waiting_room, available_aircraft_store,
    #                                                            mission_length)
