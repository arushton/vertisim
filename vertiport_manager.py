import simpy
import networkx as nx
from typing import Any, Dict
from utils.units import sec_to_ms
from utils.distribution_generator import DistributionGenerator
from utils.helpers import get_passenger_ids_from_passenger_list
from battery_model import BatteryModel
from utils.calc_required_charge_time_from_required_energy import calc_required_charge_time_from_required_energy


class VertiportManager:
    def __init__(self,
                 env: object,
                 vertiport: object,
                 scheduler: object,
                 arrival_priority: int,
                 departure_priority: int,
                 taxi_config: object,
                 aircraft_fleet_specs: Dict,
                 aircraft_energy_consumption_data: Dict,
                 charging_time_distribution_params: Dict,
                 passenger_distributions: Dict,
                 max_flight_waiting_time: int,
                 charging_interuption: bool,
                 charger_efficiency: float,
                 charger_max_charge_rate: float,
                 min_reserve_soc: float,
                 event_saver: object):
        self.env = env
        self.vertiport = vertiport
        self.scheduler = scheduler
        self.arrival_priority = arrival_priority
        self.departure_priority = departure_priority
        self.taxi_config = taxi_config
        self.aircraft_fleet_specs = aircraft_fleet_specs
        self.charging_time_distribution_params = charging_time_distribution_params
        self.passenger_distributions = passenger_distributions
        self.max_flight_waiting_time = max_flight_waiting_time
        self.charging_interuption = charging_interuption
        self.charger_efficiency = charger_efficiency
        self.charger_max_charge_rate = charger_max_charge_rate
        self.min_reserve_soc = min_reserve_soc
        self.event_saver = event_saver
        self.charging_time_distribution = self.build_charging_time_distribution()
        self.aircraft_energy_consumption_data = aircraft_energy_consumption_data
        self.aircraft_battery_models = self.build_aircraft_battery_models(self.aircraft_fleet_specs)
        self.taxi_resource = simpy.Resource(self.env, 1)
        self.env.process(self.check_passenger_max_waiting_time_threshold())
        # self.available_aircraft_store = simpy.FilterStore(self.env) # This is stored at vertiport class
        # self.active_aircraft_store = simpy.FilterStore(self.env) # This is stored at vertiport class

    def build_charging_time_distribution(self):
        """
        Builds the charging time distribution with the given parameters
        """
        if self.charging_time_distribution_params is None:
            return None
        return DistributionGenerator(self.charging_time_distribution_params,
                                     self.charging_time_distribution_params['max_charge_duration']
                                     )

    def build_aircraft_battery_models(self, aircraft_fleet_specs):
        """
        Builds the battery models for the each aircraft model in the fleet
        """
        # TODO: Check if this wanted to be used.
        aircraft_battery_models = {}
        for aircraft_model in aircraft_fleet_specs:
            generalized_battery_model = BatteryModel(
                charger_max_charge_rate=self.charger_max_charge_rate,
                charger_efficiency=self.charger_efficiency,
                min_reserve_soc=self.min_reserve_soc)
            aircraft_battery_models[aircraft_model] = generalized_battery_model.compute_charging_process_params(
                battery_size=aircraft_fleet_specs[aircraft_model]['battery_capacity']
            )
        return aircraft_battery_models

    def assign_fato(self, parking_space: str, rule: str = 'min') -> str:
        """
        Finds a FATO pad for the given parking space with the given rule

        Parameters
        ----------
        parking_space: str
            Assigned parking space for arriving aircraft
        rule: str
            Rule for assigning FATO pad. 'min' for searching closest fato pad

        Returns
        -------
        str
            assigned FATO ID for arriving aircraft
        """
        available_fato_pads = {}
        for fato in self.vertiport.fato_store.items:
            # If that edge exists reserve the FATO
            if self.vertiport.vertiport_layout.G.has_edge(fato.fato_id, parking_space):
                # FATO id's last digit needs to match with the parking pad's second to last digit
                # if (fato.fato_id[-1] == parking_space[-2])
                taxi_length = nx.dijkstra_path_length(self.vertiport.vertiport_layout.G,
                                                      parking_space, fato.fato_id)
                available_fato_pads[fato.fato_id] = taxi_length

        # Find the key of shortest distance
        if rule == 'min':
            return min(available_fato_pads, key=available_fato_pads.get)
        else:
            return max(available_fato_pads, key=available_fato_pads.get)

    def request_fato(self, assigned_fato_resource, operation_type):
        if operation_type == 'arrival':
            priority = self.arrival_priority
        elif operation_type == 'departure':
            priority = self.departure_priority
        else:
            raise ValueError("Operation type is not valid. Operation type should be 'arrival' or 'departure'.")
        return assigned_fato_resource.fato_resource.request(priority=priority)

    def request_taxi_resource(self):
        if self.taxi_config.is_simultaneous_taxi_and_take_off_allowed == False:
            return self.taxi_resource.request()
        else:
            return None

    def release_taxi_usage_request(self, taxi_usage_request):
        if taxi_usage_request is not None:
            self.taxi_resource.release(taxi_usage_request)

    def generate_taxi_route_nodes(self, source: str, target: str) -> [list, float]:
        """
        Returns a taxi route as a list between assigned FATO pad and parking
        space.

        Parameters
        ----------
        source : str
            FATO pad ID or parking space ID assigned by the skyport manager
        target : str
            FATO pad ID or parking space ID assigned by the skyport manager

        Returns
        -------
        list
            list of nodes that an aircraft has to follow for its taxi
        float
            Total taxi length
        """
        taxi_route = nx.astar_path(self.vertiport.vertiport_layout.G, source, target)
        total_taxi_length = nx.astar_path_length(self.vertiport.vertiport_layout.G, source, target)

        return taxi_route, round(total_taxi_length, 2)

    @staticmethod
    def generate_taxi_route_edges(taxi_route: list) -> list:
        """
        Generates taxi route edges from taxi route nodes.

        Parameters
        ----------
        taxi_route : list
            list of nodes that an aircraft has to follow for its taxi

        Returns
        -------
        list
            list of edges that an aircraft has to follow for its taxi
        """
        return [
            {taxi_route[count], taxi_route[count + 1]}
            for count in range(len(taxi_route) - 1)
        ]

    def get_parking_pad(self) -> str:
        """
        Gets an available parking space from parking_space_store.

        returns
        -------
        str
            parking space ID
        """
        return self.vertiport.parking_space_store.get()

    def release_parking_space(self, departure_parking_space: str) -> None:
        """
        Releases the parking space of the departing aircraft
        """
        self.vertiport.parking_space_store.put(departure_parking_space)

    def get_required_energy_for_mission(self, aircraft: object, pax: int, distance: float) -> float:
        """
        Calculates the required energy (in kW) for the mission for the given type of aircraft
        :param aircraft:
        :param pax:
        :param distance:
        :return: Required energy (in kW) for the mission
        """
        return self.aircraft_energy_consumption_data[aircraft.aircraft_model][
            self.aircraft_energy_consumption_data[aircraft.aircraft_model]['range'] == distance][
            f'kW_pax_{pax}'].values[0]

    def convert_energy_to_time(self, mission_required_energy: float, initial_soc: int, aircraft_charging_df) -> float:
        """
        Converts energy (in kW) to time (in minutes) for the given aircraft
        :param mission_required_energy: Required energy (in kW) for the mission
        :param initial_soc: Initial state of charge of the aircraft
        :param aircraft_charging_df: Charging process df for the given aircraft
        :return: Charge time (in ms)
        """
        return calc_required_charge_time_from_required_energy(
            mission_required_energy=mission_required_energy,
            initial_soc=initial_soc,
            min_reserve_soc=self.min_reserve_soc,
            df=aircraft_charging_df
        )

    def put_aircraft_into_available_aircraft_store(self, aircraft):
        """
        Puts the aircraft into the available aircraft store
        :param aircraft:
        :return:
        """
        self.vertiport.available_aircraft_store.put(aircraft)

    def get_aircraft_from_available_aircraft_store(self, tail_number):
        """
        Gets the aircraft that has the lowest battery and can complete the mission
        :return: object
        """
        return self.vertiport.available_aircraft_store.get(lambda aircraft: aircraft.tail_number == tail_number)

    # def put_aircraft_into_active_aircraft_store(self, aircraft):
    #     """
    #     Puts the aircraft into the active aircraft store
    #     :param aircraft:
    #     :return:
    #     """
    #     self.active_aircraft_store.put(aircraft)

    # def get_aircraft_from_active_aircraft_store(self, tail_number):
    #     """
    #     Gets the aircraft from the active aircraft store
    #     :param tail_number:
    #     :return:
    #     """
    #     return self.active_aircraft_store.get(lambda aircraft: aircraft.tail_number == tail_number)

    def get_mission_length(self, dest_vertiport_id: int) -> float:
        """
        Returns the mission length given the destination vertiport ID
        """
        return self.vertiport.vertiport_distances[dest_vertiport_id]

    def trigger_scheduler(self, dest_vertiport_id: int, passengers_waiting_room: simpy.Store):
        if departing_passengers := self.scheduler.check_waiting_room(current_waiting_room=passengers_waiting_room):
            # Save passenger group completion time
            for passenger in departing_passengers:
                self.event_saver.save_passenger_waiting_room_departure_time(agent_id=passenger.passenger_id,
                                                                            waiting_room_id=dest_vertiport_id,
                                                                            agent_type='passenger')
            yield self.env.process(self.reserve_aircraft(departing_passengers))
            # yield self.env.process(self.simulate_passenger_departure(departing_passengers))

    def reserve_aircraft(self, departing_passengers: list):
        # Get the first available aircraft
        aircraft = yield self.vertiport.available_aircraft_store.get()

        # After allocating an aircraft, checks the waiting room again. If there are newcomers add them to the flight
        # list
        if len(departing_passengers) < self.scheduler.aircraft_capacity and \
                len(departing_passengers[0].waiting_room_store.items) > 0:
            departing_passengers.extend(self.scheduler.last_call_check(
                current_waiting_room=departing_passengers[0].waiting_room_store,
                num_departing_passengers=len(departing_passengers)))

        # Save the aircraft allocation time
        self.event_saver.save_aircraft_allocation_time(parking_pad_id=aircraft.parking_space_id,
                                                       agent_id=aircraft.tail_number,
                                                       aircraft_model=aircraft.aircraft_model,
                                                       agent_type='aircraft')
        # Save passenger-flight assignment time
        for passenger in departing_passengers:
            self.event_saver.save_passenger_flight_assignment_time(passenger_id=passenger.passenger_id,
                                                                   agent_type='passenger')
        self.event_saver.save_flight_info(tail_number=aircraft.tail_number,
                                          passengers=get_passenger_ids_from_passenger_list(departing_passengers),
                                          aircraft_model=aircraft.aircraft_model,
                                          event_type='flight_assignment')

        # Simulate aircraft departure process
        yield self.env.process(
            self.simulate_aircraft_departure_process(aircraft=aircraft, departing_passengers=departing_passengers)
        )

    def check_passenger_max_waiting_time_threshold(self):
        """
        Checks all of the waiting rooms. If there are passengers who are waiting
        more than max_flight_waiting_time, it creates a flight for those passengers immediately.
        """
        while True:
            # Check the waiting rooms every max_waiting_time/2.
            yield self.env.timeout(round(sec_to_ms(self.max_flight_waiting_time) / 2))

            if departing_passenger_groups := self.scheduler.check_max_waiting_time_threshold():
                for departing_passengers in departing_passenger_groups:
                    yield self.env.process(self.reserve_aircraft(departing_passengers))
                flight_queue = [self.env.process(self.reserve_aircraft(departing_passengers)) for departing_passengers
                                in departing_passenger_groups]

                yield self.env.all_of(flight_queue)

    # PASSENGER RELATED METHODS
    # -------------------------
    def put_passenger_into_waiting_room(self, passenger: object) -> None:
        """
        Puts the passenger into the waiting room based on their flight destination and triggers scheduler
        :param passenger:
        :return:
        """
        # Save the time when the passenger enters the waiting room
        self.event_saver.save_passenger_waiting_room_arrival_time(passenger_id=passenger.passenger_id,
                                                                  waiting_room_id=passenger.dest_vertiport_id)
        passenger.waiting_room_arrival_time = self.env.now

        passengers_waiting_room = self.vertiport.waiting_room_stores[f'waiting_room_{passenger.dest_vertiport_id}']
        passengers_waiting_room.put(passenger)
        passenger.waiting_room_store = passengers_waiting_room
        yield self.env.process(self.trigger_scheduler(passenger.dest_vertiport_id, passengers_waiting_room))

    def simulate_passenger_arrival(self, passenger):
        """ Simulate passenger."""
        # Save passenger creation time
        self.event_saver.save_agent_creation_time(agent_id=passenger.passenger_id,
                                                  agent_type='passenger')
        # Simulate agent's walk from car to the vertiport entrance
        yield self.env.process(passenger.walk_to_entrance())
        # Save the time when the passenger arrives at the vertiport entrance
        self.event_saver.save_passenger_vertiport_entrance_arrival_time(passenger_id=passenger.passenger_id)
        # Simulate agent's security check
        yield self.env.process(passenger.security_check())
        # Save the time when the passenger finishes the security check
        self.event_saver.save_passenger_security_check_finish_time(passenger_id=passenger.passenger_id)
        # Put the passenger into the waiting room
        yield self.env.process(self.put_passenger_into_waiting_room(passenger))

    # def simulate_passenger_departure(self, departing_passengers):
    #     for passenger in departing_passengers:
    #         yield self.env.process(passenger.waiting_room_to_boarding_gate())
    #         self.event_saver.save_passenger_boarding_gate_arrival_time(agent_id=passenger.passenger_id)

    # Add the passenger to a flight
    # yield self.env.process(FlightGeneration(self.env, maxWaitingTime, aircraftCapacity,
    #                           self.vertiport).checkWaitingRoom(currentWaitingRoom))

    # AIRCRAFT RELATED METHODS
    # -------------------------

    def get_taxi_instructions(self, assigned_fato_id, parking_space_id):
        # Get the taxi route nodes from vertiport manager
        taxi_route, _ = self.generate_taxi_route_nodes(
            assigned_fato_id, parking_space_id)

        # Get the taxi route edges from vertiport manager
        taxi_route_edges = self.generate_taxi_route_edges(taxi_route)
        return taxi_route, taxi_route_edges

    def call_fato_resource(self, assigned_fato_id: str) -> object:
        """
        Calls the assigned fato pad resource from fato_store of vertiport manager

        Parameters
        ----------
        assigned_fato_id : str
            Assigned TLOF pad ID by the vertiport manager.
        priority : int
            Priority for using the TLOF pad resource. Lower value prioritized

        Returns
        -------
        FatoResource class
            Class object that provides the FATO resource by request.
        """
        fato_list = [fato.fato_id for fato in self.vertiport.fato_store.items]
        fato_index = fato_list.index(assigned_fato_id)
        return self.vertiport.fato_store.items[fato_index]

    # TODO: Check all
    def simulate_aircraft_arrival_process(self, aircraft):
        self.event_saver.save_agent_creation_time(agent_id=aircraft.tail_number,
                                                  agent_type='aircraft',
                                                  aircraft_model=aircraft.aircraft_model)
        # parking space and FATO reservation for landing
        parking_space = yield self.get_parking_pad()
        parking_space_id = parking_space.parking_space_id

        # Save them to use for departure
        aircraft.parking_space = parking_space
        aircraft.parking_space_id = parking_space_id

        # Currently, vertiport manager assigns the closest FATO
        assigned_fato_id = self.assign_fato(parking_space_id)

        # Aircraft calls the FATO resource that will be requested.
        assigned_fato_resource = self.call_fato_resource(assigned_fato_id)
        # Request for FATO pad usage
        aircraft_fato_usage_request = self.request_fato(
            assigned_fato_resource=assigned_fato_resource,
            operation_type='arrival'
        )
        yield aircraft_fato_usage_request

        # Landing process
        yield self.env.process(
            aircraft.aircraft_landing_process(
                time_descend_transition=aircraft.time_descend_transition,
                time_hover_descend=aircraft.time_hover_descend,
                time_rotor_spin_down=aircraft.time_rotor_spin_down,
                landing_fato_id=assigned_fato_id,
                time_post_landing_safety_checks=aircraft.time_post_landing_safety_checks,
                time_tug_connection=aircraft.time_tug_connection
            )
        )

        # Get the taxi route
        taxi_route, taxi_route_edges = self.get_taxi_instructions(
            assigned_fato_id,
            parking_space_id
        )

        # Taxi-in process
        yield self.env.process(
            aircraft.taxi(
                taxi_route=taxi_route,
                taxi_route_edges=taxi_route_edges,
                assigned_fato_resource=assigned_fato_resource,
                parking_space_id=parking_space_id,
                parking_space=parking_space,
                aircraft_fato_usage_request=aircraft_fato_usage_request,
                operation_type='arrival',
                departing_passengers=None
            )
        )

        # Charge the aircraft
        yield self.env.process(
            aircraft.charge_aircraft(
                charge_time=aircraft.time_charging,
                time_passenger_embark_disembark=aircraft.time_passenger_embark_disembark,
                parking_space=parking_space,
                time_pre_charging_processes=aircraft.time_pre_charging_processes,
                time_post_charging_processes=aircraft.time_post_charging_processes,
                time_charging_plug_disconnection=aircraft.time_charging_plug_disconnection,
                shared_charger=self.vertiport.shared_charger_sets
            )
        )

        # Take out the aircraft from active aircraft list and put it into available aircraft list
        # self.active_aircraft_store.get(lambda filt: filt == aircraft.tail_number)
        self.put_aircraft_into_available_aircraft_store(aircraft)

    def simulate_aircraft_departure_process(self, aircraft, departing_passengers):
        # Save passenger boarding time
        for passenger in departing_passengers:
            self.event_saver.save_passenger_boarding_finish_time(passenger_id=passenger.passenger_id,
                                                                 aircraft_id=aircraft.tail_number)
        # Aircraft take off request
        assigned_fato_id = self.assign_fato(aircraft.parking_space_id)

        # Aircraft calls the FATO resource that will be requested.
        assigned_fato_resource = self.call_fato_resource(assigned_fato_id)

        # Request for FATO pad usage
        aircraft_fato_usage_request = self.request_fato(
            assigned_fato_resource=assigned_fato_resource,
            operation_type='departure'
        )
        yield aircraft_fato_usage_request

        taxi_usage_request = self.request_taxi_resource()
        if taxi_usage_request is not None:
            yield taxi_usage_request

        # Save pushback time
        self.event_saver.save_pushback_info(
            pushback_location=aircraft.parking_space_id,
            agent_id=aircraft.tail_number,
            aircraft_model=aircraft.aircraft_model
        )

        # Taxi-out process
        taxi_route, taxi_route_edges = self.get_taxi_instructions(aircraft.parking_space_id, assigned_fato_id)
        yield self.env.process(
            aircraft.taxi(
                taxi_route=taxi_route,
                taxi_route_edges=taxi_route_edges,
                assigned_fato_resource=assigned_fato_resource,
                parking_space_id=aircraft.parking_space_id,
                parking_space=aircraft.parking_space,
                aircraft_fato_usage_request=aircraft_fato_usage_request,
                operation_type='departure',
                departing_passengers=departing_passengers
            )
        )

        # Save take-off info
        self.event_saver.save_flight_info(tail_number=aircraft.tail_number,
                                          passengers=get_passenger_ids_from_passenger_list(departing_passengers),
                                          aircraft_model=aircraft.aircraft_model,
                                          event_type='take_off')
        # Take-off process
        yield self.env.process(
            aircraft.aircraft_take_off_process(
                time_rotor_spin_up=aircraft.time_rotor_spin_up,
                time_hover_climb=aircraft.time_hover_climb,
                time_climb_transition=aircraft.time_climb_transition,
                take_off_fato_id=assigned_fato_id,
                time_pre_take_off_check_list=aircraft.time_pre_take_off_check_list,
                time_tug_disconnection=aircraft.time_tug_disconnection,
                departing_passengers=departing_passengers
            )
        )

        self.release_taxi_usage_request(taxi_usage_request)
        # Release the FATO
        assigned_fato_resource.fato_resource.release(aircraft_fato_usage_request)
