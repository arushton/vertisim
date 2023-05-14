from typing import Dict, Union, Callable, Optional, Dict, List
from utils.units import sec_to_ms
from collections import defaultdict


class Scheduler:
    def __init__(self, env: object,
                 vertiports: object,
                 vertiport_manager: object,
                 aircraft_capacity: int = None):
        self.env = env
        self.vertiports = vertiports
        self.aircraft_capacity = aircraft_capacity
        self.vertiport_manager = vertiport_manager
        self.fixed_flight_schedule = None

    def initiate_fixed_schedule_from_file(self):
        # TODO: Implement this method
        # Timeout the event times from the current time. Then start the arrival process
        # for tail_number in self.fixed_flight_schedule.tail_number:
        pass

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
