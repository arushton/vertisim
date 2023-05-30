import simpy
import networkx as nx
from typing import Any, Dict
from utils.units import sec_to_ms, ms_to_sec
from utils.distribution_generator import DistributionGenerator
from utils.weighted_random_chooser import random_choose_exclude_element
from utils.helpers import get_passenger_ids_from_passenger_list, calculate_passenger_consolidation_time, check_whether_node_exists
from aircraft.battery_model import BatteryModel
import pandas as pd
from collections import defaultdict
from utils.calc_required_charge_time_from_required_energy import calc_required_charge_time_from_required_energy
from typing import List, Union


class VertiportManager:
    def __init__(self,
                 env: object,
                 vertiports: Dict,
                 vertiport_ids: List,
                 scheduler: object,
                 arrival_priority: int,
                 departure_priority: int,
                 airspace: object,
                 taxi_config: object,
                 only_aircraft_simulation: bool,
                 aircraft_params: Dict,
                 vertiport_distances: pd.DataFrame,
                 aircraft_energy_consumption_data: Dict,
                 passenger_distributions: Dict,
                 max_flight_waiting_time: int,
                 charging_interuption: bool,
                 event_saver: object,
                 network_simulation: bool,
                 fixed_schedule: bool,
                 node_locations: Dict):
        self.env = env
        self.vertiports = vertiports
        self.vertiport_ids = vertiport_ids
        self.scheduler = scheduler
        self.airspace = airspace
        self.arrival_priority = arrival_priority
        self.departure_priority = departure_priority
        self.taxi_config = taxi_config
        self.only_aircraft_simulation = only_aircraft_simulation
        self.aircraft_params = aircraft_params
        self.vertiport_distances = vertiport_distances
        self.aircraft_energy_consumption_data = aircraft_energy_consumption_data
        self.passenger_distributions = passenger_distributions
        self.max_flight_waiting_time = max_flight_waiting_time
        self.charging_interuption = charging_interuption
        self.event_saver = event_saver
        self.network_simulation = network_simulation
        self.node_locations = node_locations
        self.fixed_schedule = fixed_schedule
        self.aircraft_agents = {}
        self.passenger_agents = {}
        self.flight_times = defaultdict(list)
        # if not self.network_simulation:
        self.charging_time_distribution = self.build_charging_time_distribution()
        self.aircraft_battery_models = self.build_aircraft_battery_models()
        self.taxi_resource = simpy.Resource(self.env, 1)
        if (
            not self.only_aircraft_simulation
            and not self.fixed_schedule
            and self.max_flight_waiting_time
        ):
            self.env.process(self.check_passenger_max_waiting_time_threshold())
        # self.available_aircraft_store = simpy.FilterStore(self.env) # This is stored at vertiport class
        # self.active_aircraft_store = simpy.FilterStore(self.env) # This is stored at vertiport class

    # AIRCRAFT RELATED METHODS
    # -------------------------
    def build_charging_time_distribution(self):
        """
        Builds the charging time distribution with the given parameters
        """
        if self.aircraft_params['charging_time_dist'] is None:
            return None
        return DistributionGenerator(self.aircraft_params['charging_time_dist'])

    def build_aircraft_battery_models(self) -> Dict[Any, pd.DataFrame]:
        """
        Builds the battery charging lookup tables for the aircraft model for each vertiport.
        """
        # TODO: Currently, we support single aircraft model for all vertiports. However, each vertiport can
        # have different charger models. We might need to support different aircraft models in the future but not urgent/crucial
        return {vertiport_name: 
            BatteryModel(charger_model=vertiport.charger_model, 
                        min_reserve_soc=self.aircraft_params['min_reserve_soc']).
                        charge_process(battery_capacity=self.aircraft_params['battery_capacity'])
                for vertiport_name, vertiport in self.vertiports.items()
        }

    def assign_fato(self, vertiport_id: Any, parking_space: str, fato_id: str = None, rule: str = 'min') -> str:
        """
        Finds a FATO pad for the given parking space with the given rule. If there is no parking pad
        on the vertiport, choose the fato resource with zero users or the least queued fato

        Parameters
        ----------
        vertiport_id : Any
            Vertiport ID
        parking_space: str
            Assigned parking space for arriving aircraft
        rule: str
            Rule for assigning FATO pad. 'min' for searching closest fato pad

        Returns
        -------
        str
            assigned FATO ID for arriving aircraft
        """
        if fato_id is not None:
            return fato_id

        num_parking_pad = self.vertiports[vertiport_id].vertiport_layout.num_parking_pad
        if  num_parking_pad == 0:
            fato_pads = {}
            for fato in self.vertiports[vertiport_id].fato_store.items:
                # Choose the fato resource with the zero users or the least queued users
                fato_pads[fato.resource_id] = len(fato.fato_resource.queue)
                if fato.fato_resource.count == 0:
                    return fato.resource_id
            return min(fato_pads, key=fato_pads.get)
                    

        available_fato_pads = {}
        for fato in self.vertiports[vertiport_id].fato_store.items:
            # If that edge exists reserve the FATO
            if self.vertiports[vertiport_id].vertiport_layout.G.has_edge(fato.resource_id, parking_space):
                # FATO id's last digit needs to match with the parking pad's second to last digit
                # if (fato.resource_id[-1] == parking_space[-2])
                taxi_length = round(nx.dijkstra_path_length(self.vertiports[vertiport_id].vertiport_layout.G,
                                                      parking_space, fato.resource_id))
                available_fato_pads[fato.resource_id] = taxi_length

        # Find the key of shortest distance
        if rule == 'min':
            return min(available_fato_pads, key=available_fato_pads.get)
        else:
            return max(available_fato_pads, key=available_fato_pads.get)

    def request_fato(self, assigned_fato_resource: object, operation_type: str, priority: int = 1) -> object:
        """
        Requests the assigned fato pad resource from fato_store of vertiport manager

        Parameters
        ----------
        assigned_fato_resource : object
            Assigned TLOF pad resource by the vertiport manager.
        operation_type : str
            Operation type of the aircraft. 'arrival' or 'departure'

        Returns
        -------
        FatoResource class
            Class object that provides the FATO resource by request.
        """
        if operation_type == 'arrival':
            priority = self.arrival_priority
        elif operation_type == 'departure':
            priority = self.departure_priority
        else:
            raise ValueError("Operation type is not valid. Operation type should be 'arrival' or 'departure'.")
        return assigned_fato_resource.fato_resource.request(priority=priority)

    def call_fato_resource(self, vertiport_id: Any, assigned_fato_id: str) -> object:
        """
        Calls the assigned fato pad resource from fato_store of vertiport manager

        Parameters
        ----------
        vertiport_id : Any
            Vertiport ID
        assigned_fato_id : str
            Assigned TLOF pad ID by the vertiport manager.
        priority : int
            Priority for using the TLOF pad resource. Lower value prioritized

        Returns
        -------
        FatoResource class
            Class object that provides the FATO resource by request.
        """
        fato_list = [fato.resource_id for fato in self.vertiports[vertiport_id].fato_store.items]
        fato_index = fato_list.index(assigned_fato_id)
        return self.vertiports[vertiport_id].fato_store.items[fato_index]

    def get_taxi_instructions(self, vertiport_id: Any, assigned_fato_id: str, parking_space_id: str):
        """
        Gets the taxi route nodes and edges from vertiport manager
        
        Parameters
        ----------
        vertiport_id : Any
            Vertiport ID
        assigned_fato_id : str
            Assigned FATO ID by the vertiport manager.
        parking_space_id : str
            Assigned parking space ID by the vertiport manager.

        Returns
        -------
        taxi_route : list
            List of taxi route nodes
        taxi_route_edges : list
            List of taxi route edges
        """
        num_parking_pad = self.vertiports[vertiport_id].vertiport_layout.num_parking_pad
        if  num_parking_pad == 0:
            return [], []        
        # Get the taxi route nodes from vertiport manager
        taxi_route, _ = self.generate_taxi_route_nodes(vertiport_id, 
                                                       assigned_fato_id, 
                                                       parking_space_id)

        # Get the taxi route edges from vertiport manager
        taxi_route_edges = self.generate_taxi_route_edges(vertiport_id=vertiport_id, 
                                                          taxi_route=taxi_route)
        return taxi_route, taxi_route_edges

    def request_taxi_resource(self, vertiport_id: Any):
        """
        Requests the taxi resource from taxi manager

        Parameters
        ----------
        vertiport_id : Any
            Vertiport ID

        Returns
        -------
        taxi_usage_request : object
            Taxi usage request object

        """
        if self.taxi_config.is_simultaneous_taxi_and_take_off_allowed == False:
            return self.vertiports[vertiport_id].taxi_resource.request()
        else:
            return None

    def release_taxi_usage_request(self, vertiport_id, taxi_usage_request):
        """
        Releases the taxi resource from usage

        Parameters
        ----------
        taxi_usage_request : object
            Taxi usage request object

        Returns
        -------
        None
        """
        if taxi_usage_request is not None:
            self.vertiports[vertiport_id].taxi_resource.release(taxi_usage_request)

    def request_fix_resource(self, flight_direction: str, operation_type: str):
        """
        Requests the fix resource from vertiport manager
        """
        if operation_type == 'arrival':
            arrival_fix_resource = self.get_second_to_last_airlink_resource(flight_direction=flight_direction)
            return arrival_fix_resource.request(), arrival_fix_resource            
        elif operation_type == 'departure':
            departure_fix_resource = self.get_second_airlink_resource(flight_direction=flight_direction)
            return departure_fix_resource.request(), departure_fix_resource 
        
    def release_fix_resource(self, aircraft: object, operation: str):
        """
        Releases the fix resource from usage

        Parameters
        ----------
        aircraft : object
            Aircraft object
        operation : str
            Operation type of the aircraft. 'arrival' or 'departure'

        Returns
        -------
        None
        """
        if operation == 'arrival':
            aircraft.arrival_fix_resource.release(aircraft.arrival_fix_usage_request)
            aircraft.arriaval_fix_usage_request = None
            aircraft.arrival_fix_resource = None
        elif operation == 'departure':
            aircraft.departure_fix_resource.release(aircraft.departure_fix_usage_request)
            aircraft.departure_fix_usage_request = None
            aircraft.departure_fix_resource = None
        else:
            raise ValueError("Operation type is not valid. Operation type should be 'arrival' or 'departure'.")

    def get_first_airlink_resource(self, flight_direction: str):
        # First airlink resource is hover fix
        return next(iter(self.airspace.airlink_resources[flight_direction].values()))
    
    def get_first_airlink_node_id(self, flight_direction: str):
        # First airlink resource is hover fix
        return next(iter(self.airspace.airlink_resources[flight_direction].keys()))
    
    def get_second_airlink_resource(self, flight_direction: str):
        # Second airlink resource is the departure fix
        values_iterator = iter(self.airspace.airlink_resources[flight_direction].values())
        next(values_iterator)
        return next(values_iterator)

    def get_second_airlink_node_id(self, flight_direction: str):
        keys_iterator = iter(self.airspace.airlink_resources[flight_direction].keys())
        next(keys_iterator)
        return next(keys_iterator)    
    
    def get_third_airlink_resource(self, flight_direction: str):
        # Third airlink resource is the first waypoint
        values_iterator = iter(self.airspace.airlink_resources[flight_direction].values())
        next(values_iterator)
        next(values_iterator)
        return next(values_iterator)
    
    def get_third_airlink_node_id(self, flight_direction: str):
        keys_iterator = iter(self.airspace.airlink_resources[flight_direction].keys())
        next(keys_iterator)
        next(keys_iterator)
        return next(keys_iterator)

    def get_last_airlink_resource(self, flight_direction: str):
        # Last airlink resource is the hover descend fix
        return list(self.airspace.airlink_resources[flight_direction].values())[-1]
    
    def get_last_airlink_node_id(self, flight_direction: str):
        return list(self.airspace.airlink_resources[flight_direction].keys())[-1]
    
    def get_second_to_last_airlink_resource(self, flight_direction: str):
        # Second to last airlink resource is the final approach fix
        return list(self.airspace.airlink_resources[flight_direction].values())[-2]
    
    def get_second_to_last_airlink_node_id(self, flight_direction: str):
        return list(self.airspace.airlink_resources[flight_direction].keys())[-2]
    
    def get_third_to_last_airlink_resource(self, flight_direction: str):
        # Third to last airlink resource is the holding unit
        return list(self.airspace.airlink_resources[flight_direction].values())[-3]
    
    def get_third_to_last_airlink_node_id(self, flight_direction: str):
        return list(self.airspace.airlink_resources[flight_direction].keys())[-3]

    def generate_taxi_route_nodes(self, vertiport_id: str, source: str, target: str) -> Union[list, float]:
        """
        Returns a taxi route as a list between assigned FATO pad and parking
        space.

        Parameters
        ----------
        vertiport_id : str
            Vertiport ID
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
        num_parking_pad = self.vertiports[vertiport_id].vertiport_layout.num_parking_pad
        if  num_parking_pad == 0:
            return [], 0
        
        taxi_route = nx.astar_path(self.vertiports[vertiport_id].vertiport_layout.G, source, target)
        total_taxi_length = nx.astar_path_length(self.vertiports[vertiport_id].vertiport_layout.G, source, target)

        return taxi_route, round(total_taxi_length, 2)

    def generate_taxi_route_edges(self, vertiport_id, taxi_route: list) -> list:
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
        num_parking_pad = self.vertiports[vertiport_id].vertiport_layout.num_parking_pad
        if  num_parking_pad == 0:
            return []
                
        return [
            {taxi_route[count], taxi_route[count + 1]}
            for count in range(len(taxi_route) - 1)
        ]

    def get_parking_pad(self, vertiport_id: Any, parking_space_id: Any = None) -> str:
        """
        Gets an available parking space from parking_space_store.

        Parameters
        ----------
        vertiport_id : str
            Vertiport ID

        Returns
        -------
        str
            Parking space ID
        """
        if parking_space_id is not None:
            if not check_whether_node_exists(self.node_locations, parking_space_id):
                raise ValueError(
                    f"Node {parking_space_id} does not exist in the vertiport {vertiport_id}"
                )
            return self.vertiports[vertiport_id].parking_space_store.get(lambda x: x.resource_id == parking_space_id)
        return self.vertiports[vertiport_id].parking_space_store.get()

    def release_parking_space(self, vertiport_id: Any, departure_parking_space: str) -> None:
        """
        Releases the parking space of the departing aircraft

        Parameters
        ----------
        vertiport_id : str
            Vertiport ID
        departure_parking_space : str
            Parking space ID of the departing aircraft

        Returns
        -------
        None
        """
        self.vertiports[vertiport_id].parking_space_store.put(departure_parking_space)

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
            min_reserve_soc=self.aircraft_params['min_reserve_soc'],
            df=aircraft_charging_df
        )

    def put_aircraft_into_available_aircraft_store(self, vertiport_id: Any, aircraft: object) -> None:
        """
        Puts the aircraft into the available aircraft store
        :param aircraft:
        :return:
        """
        self.vertiports[vertiport_id].available_aircraft_store.put(aircraft)

    def get_aircraft_from_available_aircraft_store(self, vertiport_id: Any, tail_number: str) -> object:
        """
        Gets the aircraft that has the lowest battery and can complete the mission
        :return: object
        """
        return self.vertiports[vertiport_id].available_aircraft_store.get(lambda aircraft: aircraft.tail_number == tail_number)

    def check_num_available_aircraft(self, vertiport_id: Any) -> int:
        """
        Checks the number of available aircraft in the available aircraft store
        :return: int
        """
        return len(self.vertiports[vertiport_id].available_aircraft_store.items)    

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

    def get_mission_length(self, origin_vertiport_id: Any, destination_vertiport_id: Any) -> float:
        """
        Returns the mission length given the destination vertiport ID
        """
        return self.vertiport_distances[(self.vertiport_distances['origin_vertiport_id'] == origin_vertiport_id) & 
                                        (self.vertiport_distances['destination_vertiport_id'] == destination_vertiport_id)]['distance_miles'].values[0]
    
    def trigger_scheduler(self, origin_vertiport_id, destination_vertiport_id: int, passengers_waiting_room: simpy.Store):
        if departing_passengers := self.scheduler.check_waiting_room(current_waiting_room=passengers_waiting_room):
            # Save passenger group completion time
            for passenger in departing_passengers:
                self.event_saver.save_agent_state(agent=passenger, agent_type='passenger', event='passenger_consolidation')

            # Save passenger consolidation time
            self.event_saver.save_passenger_group_consolidation_time(
                vertiport_id=origin_vertiport_id,
                passenger_ids=get_passenger_ids_from_passenger_list(departing_passengers),
                wr_number=destination_vertiport_id,
                consolidation_time=calculate_passenger_consolidation_time(departing_passengers)
            )

            # Increase passenger queue count
            self.event_saver.update_passenger_departure_queue_counter(vertiport_id=origin_vertiport_id, queue_update=1)

            yield self.env.process(self.reserve_aircraft(origin_vertiport_id=origin_vertiport_id,
                                                         destination_vertiport_id=destination_vertiport_id,
                                                         departing_passengers=departing_passengers)
                                                         )    

    def reserve_aircraft(self, origin_vertiport_id: Any, destination_vertiport_id: int, departing_passengers: list, tail_number: str = None):
        # Start tracking aircraft allocation time
        aircraft_allocation_start_time = self.env.now
        # Retrieve aircraft from the store
        aircraft = yield self.retrieve_aircraft(origin_vertiport_id, tail_number)   
        # Measure and save the aircraft allocation time
        self.save_aircraft_allocation_time(origin_vertiport_id, aircraft, aircraft_allocation_start_time)

        # Check the waiting room for additional passengers if there is still space on the aircraft
        departing_passengers = self.add_additional_passengers_if_needed(origin_vertiport_id, destination_vertiport_id, departing_passengers)

        # Save aircraft allocation and idle times
        self.save_aircraft_times(origin_vertiport_id, aircraft)

        # Assign passengers to the aircraft
        aircraft.passengers_onboard = departing_passengers

        # Save total passenger waiting time and flight assignment time
        self.save_passenger_times(origin_vertiport_id, aircraft.passengers_onboard)

        # Start the passenger departure process
        self.env.process(self.simulate_passenger_departure(departing_passengers=departing_passengers))

        # Start the aircraft departure process
        yield self.env.process(
            self.simulate_aircraft_departure_process(aircraft=aircraft,
                                                    origin_vertiport_id=origin_vertiport_id, 
                                                    destination_vertiport_id=destination_vertiport_id)
        )

    def retrieve_aircraft(self, origin_vertiport_id, tail_number):
        if tail_number is None:
            return self.vertiports[origin_vertiport_id].available_aircraft_store.get()
        elif isinstance(tail_number, (int, str)):
            return self.vertiports[origin_vertiport_id].available_aircraft_store.get(lambda aircraft: aircraft.tail_number == tail_number)
        else:
            raise ValueError("Tail numbers should be a string or an integer.")

    def save_aircraft_allocation_time(self, origin_vertiport_id, aircraft, start_time):
        aircraft_allocation_end_time = self.env.now
        self.event_saver.save_aircraft_allocation_time(vertiport_id=origin_vertiport_id,
                                                    tail_number=aircraft.tail_number,
                                                    allocation_time=aircraft_allocation_end_time - start_time)

    def add_additional_passengers_if_needed(self, origin_vertiport_id, destination_vertiport_id, departing_passengers):
        waiting_room = self.vertiports[origin_vertiport_id].waiting_room_stores[destination_vertiport_id]
        if len(departing_passengers) < self.aircraft_params['pax'] and len(waiting_room.items) > 0:
            departing_passengers.extend(self.scheduler.last_call_check(
                current_waiting_room=waiting_room,
                num_departing_passengers=len(departing_passengers)))   
        return departing_passengers

    def save_aircraft_times(self, origin_vertiport_id, aircraft):
        self.event_saver.save_agent_state(agent=aircraft, agent_type='aircraft', event='aircraft_allocation')
        self.event_saver.save_aircraft_idle_time(vertiport_id=origin_vertiport_id,
                                                agent_id=aircraft.tail_number,
                                                charging_end_time=aircraft.charging_end_time)

    def save_passenger_times(self, origin_vertiport_id, passengers):
        for passenger in passengers:
            self.event_saver.save_passenger_waiting_time(vertiport_id=origin_vertiport_id,
                                                        passenger_id=passenger.passenger_id,
                                                        waiting_time=self.env.now - passenger.waiting_room_arrival_time)
            self.save_flight_assignment_times(passenger)

    def save_flight_assignment_times(self, passenger):
        self.event_saver.save_agent_state(agent=passenger, agent_type='passenger', event='flight_assignment')
        passenger.flight_assignment_time = self.env.now

    def simulate_passenger_departure(self, departing_passengers):
        self.env.process(self.simulate_passenger_departure(departing_passengers=departing_passengers))

    def simulate_aircraft_departure(self, aircraft, origin_vertiport_id, destination_vertiport_id):
        yield self.env.process(
            self.simulate_aircraft_departure_process(aircraft=aircraft,
                                                    origin_vertiport_id=origin_vertiport_id,
                                                    destination_vertiport_id=destination_vertiport_id))


    def check_passenger_max_waiting_time_threshold(self):
        """
        Checks all of the waiting rooms. If there are passengers who are waiting
        more than max_flight_waiting_time, it creates a flight for those passengers immediately.
        """
        while True:
            # Check the waiting rooms every max_waiting_time/2.
            yield self.env.timeout(round(sec_to_ms(self.max_flight_waiting_time) / 2))

            if departing_passenger_groups := self.scheduler.check_max_waiting_time_threshold(
                    sec_to_ms(self.max_flight_waiting_time)):

                for origin in departing_passenger_groups:
                    for destination in departing_passenger_groups[origin]:
                        departing_passengers = departing_passenger_groups[origin][destination]
                        for passenger in departing_passengers:
                            self.event_saver.save_agent_state(agent=passenger, agent_type='passenger', event='passenger_waiting_room_departure')   
                        # Increase passenger queue count
                        self.event_saver.update_passenger_departure_queue_counter(vertiport_id=origin, 
                                                                                queue_update=len(departing_passenger_groups))   
                        flight_queue = [self.env.process(
                            self.reserve_aircraft(origin_vertiport_id=origin, 
                                                destination_vertiport_id=departing_passengers[0].destination_vertiport_id,
                                                departing_passengers=departing_passengers))
                        ]

                    yield self.env.all_of(flight_queue)                                                                   


    # PASSENGER RELATED METHODS
    # -------------------------
    def simulate_passenger_arrival(self, passenger):
        """ Simulate passenger."""
        # Save passenger creation time
        self.event_saver.save_agent_state(agent=passenger, agent_type='passenger', event='vertiport_entrance')
        passenger.vertiport_arrival_time = self.env.now

        # Simulate agent's walk from car to the vertiport entrance
        self.env.process(passenger.walk_to_entrance())

        # Simulate agent's security check
        self.env.process(passenger.security_check())

        # Put the passenger into the waiting room
        yield self.env.process(self.put_passenger_into_waiting_room(passenger))

    def simulate_passenger_departure(self, departing_passengers):
        for passenger in departing_passengers:
            yield self.env.process(passenger.waiting_room_to_boarding_gate())
            passenger.location = f'{passenger.origin_vertiport_id}_GATE'
            self.event_saver.save_agent_state(agent=passenger, agent_type='passenger', event='boarding_gate')

    def put_passenger_into_waiting_room(self, passenger: object) -> None:
        """
        Puts the passenger into the waiting room based on their flight destination and triggers scheduler
        :param passenger:
        :return:
        """
        # Save the time when the passenger enters the waiting room
        passenger.location = f'{passenger.origin_vertiport_id}_ROOM'
        self.event_saver.save_agent_state(agent=passenger, agent_type='passenger', event='enter_waiting_room')

        passenger.waiting_room_arrival_time = self.env.now

        passengers_waiting_room = self.vertiports[passenger.origin_vertiport_id].waiting_room_stores[passenger.destination_vertiport_id]
        passengers_waiting_room.put(passenger)
        passenger.waiting_room_store = passengers_waiting_room
        if not self.fixed_schedule:
            yield self.env.process(self.trigger_scheduler(origin_vertiport_id=passenger.origin_vertiport_id,
                                                        destination_vertiport_id=passenger.destination_vertiport_id, 
                                                        passengers_waiting_room=passengers_waiting_room))

    # -------------------------

    def check_holding_aircraft(self, flight_direction: str, vertiport_id: Any):
        arrival_fix_resource = self.get_second_to_last_airlink_resource(flight_direction=flight_direction)
        if len(arrival_fix_resource.queue) > 1:
            num_queued = min(len(arrival_fix_resource.queue), self.check_num_available_aircraft(vertiport_id))
            for _ in range(num_queued):
                self.env.process(self.assign_empty_flight(vertiport_id=vertiport_id))

    def assign_empty_flight(self, vertiport_id: Any):
        # TODO: Check the waiting rooms of the other vertiports and pick the one with the highest number of passengers
        destination_id = random_choose_exclude_element(elements_list=self.vertiport_ids, 
                                                       exclude_element=vertiport_id, 
                                                       num_selection=1)[0]
        yield self.env.process(self.reserve_aircraft(origin_vertiport_id=vertiport_id,
                                                destination_vertiport_id=destination_id,
                                                departing_passengers=[]))

    def simulate_terminal_airspace_arrival_process(self, aircraft: object, arriving_passengers: list):
        holding_start = self.env.now
        
        # Increase aircraft arrival queue counter
        self.event_saver.update_aircraft_arrival_queue_counter(vertiport_id=aircraft.destination_vertiport_id,
                                                               queue_update=1)
        
        # Request arrival fix resource
        arrival_fix_usage_request, arrival_fix_resource = self.request_fix_resource(flight_direction=aircraft.flight_direction, operation_type='arrival')
        self.check_holding_aircraft(flight_direction=aircraft.flight_direction, vertiport_id=aircraft.destination_vertiport_id)
        yield arrival_fix_usage_request

        holding_end = self.env.now
        aircraft.holding_time = holding_end - holding_start
        aircraft.update_holding_energy_consumption(aircraft.holding_time)

        self.event_saver.save_aircraft_holding_time(vertiport_id=aircraft.destination_vertiport_id,
                                                    agent_id=aircraft.tail_number,
                                                    waiting_time=aircraft.holding_time)        

        aircraft.arrival_fix_resource = arrival_fix_resource
        aircraft.arrival_fix_usage_request = arrival_fix_usage_request  

        yield self.env.process(self.fato_and_parking_pad_usage_process(aircraft=aircraft))

    def fato_and_parking_pad_usage_process(self, aircraft: object):
        if aircraft.parking_space_id is None and \
            aircraft.assigned_fato_id is None and \
                self.vertiports[aircraft.destination_vertiport_id].vertiport_layout.num_parking_pad > 0:
            # Get Parking pad
            yield self.env.process(self.parking_pad_request(aircraft=aircraft))
            # Landing process
            yield self.env.process(self.simulate_landing_process(aircraft=aircraft))
            # Taxi
            yield self.env.process(self.simulate_taxi_process(aircraft=aircraft, operation_type='arrival'))
            # Charging process 
            yield self.env.process(self.aircraft_charging_process(aircraft=aircraft))  

        # Only FATO case and starting point is not a FATO
        elif aircraft.parking_space_id is None and aircraft.assigned_fato_id is None:
            # NOTE: We don't request FATO here because it will be requested in the landing_process. However
            # in the case of single FATO, we are increasing the FATO reservation time from 
            # time_descend_transition + time_hover_descend to time_descend_transition + time_hover_descend + time_descend
            # yield self.env.process(self.fato_pad_request(aircraft=aircraft, operation_type='arrival'))  

            # Landing process
            yield self.env.process(self.simulate_landing_process(aircraft=aircraft))                  
            # Charging process 
            yield self.env.process(self.aircraft_charging_process(aircraft=aircraft))           

        # If the aircraft is not assigned to a parking pad but its starting location is a FATO
        elif aircraft.parking_space_id is None and \
            aircraft.assigned_fato_id is not None and \
                self.vertiports[aircraft.destination_vertiport_id].vertiport_layout.num_parking_pad > 0:
            # Get Parking pad
            yield self.env.process(self.parking_pad_request(aircraft=aircraft))
            # Get FATO
            yield self.env.process(self.fato_pad_request(aircraft=aircraft, operation_type='arrival'))
            # Taxi
            yield self.env.process(self.simulate_taxi_process(aircraft=aircraft, operation_type='arrival'))
            # Charging process 
            yield self.env.process(self.aircraft_charging_process(aircraft=aircraft))  
        
        # Only FATO case and the starting location is a FATO
        elif aircraft.assigned_fato_id is not None:
            # Get FATO
            yield self.env.process(self.fato_pad_request(aircraft=aircraft, operation_type='arrival', fato_id=aircraft.assigned_fato_id))
            # Charging process
            yield self.env.process(self.aircraft_charging_process(aircraft=aircraft))

        # If the aircraft is assigned to a parking pad
        elif aircraft.parking_space_id is not None:
            # Get Parking pad
            yield self.env.process(self.parking_pad_request(aircraft=aircraft, parking_space_id=aircraft.parking_space_id))
            # Charging process
            yield self.env.process(self.aircraft_charging_process(aircraft=aircraft))         
    
    def parking_pad_request(self, aircraft: object, parking_space_id: Any = None):
        # parking space reservation for landing
        parking_space = yield self.get_parking_pad(vertiport_id=aircraft.destination_vertiport_id, parking_space_id=parking_space_id)
        parking_space_id = parking_space.resource_id
        # Save them to use for departure
        aircraft.parking_space = parking_space
        aircraft.parking_space_id = parking_space_id

    def fato_pad_request(self, aircraft: object, operation_type: str, fato_id: str = None):
        if operation_type == 'arrival':
            vertiport_id = aircraft.destination_vertiport_id
        elif operation_type == 'departure':
            vertiport_id = aircraft.origin_vertiport_id
        else:
            raise ValueError('Operation type for FATO request is not valid.')
        # Currently, vertiport manager assigns the closest FATO
        assigned_fato_id = self.assign_fato(vertiport_id=vertiport_id,
                                            parking_space=aircraft.parking_space_id,
                                            fato_id=fato_id)
        aircraft.assigned_fato_id = assigned_fato_id

        # Aircraft calls the FATO resource that will be requested.
        assigned_fato_resource = self.call_fato_resource(vertiport_id=vertiport_id,
                                                        assigned_fato_id=assigned_fato_id)
        aircraft.assigned_fato_resource = assigned_fato_resource

        if operation_type == 'departure':
            # Increase the aircraft departure queue counter
            self.event_saver.update_aircraft_departure_queue_counter(vertiport_id=vertiport_id,
                                                                    queue_update=1)            

        # Request for FATO pad usage
        aircraft_fato_usage_request = self.request_fato(
            assigned_fato_resource=assigned_fato_resource,
            operation_type=operation_type)
        yield aircraft_fato_usage_request
        aircraft.aircraft_fato_usage_request = aircraft_fato_usage_request

        if operation_type == 'departure':
            # Increase the aircraft departure queue counter
            self.event_saver.update_aircraft_departure_queue_counter(vertiport_id=vertiport_id,
                                                                    queue_update=-1)     

        if operation_type == 'arrival' and \
            self.vertiports[aircraft.destination_vertiport_id].vertiport_layout.num_parking_pad == 0:
            # If there is no parking pad then aircraft will be parked on FATO
            aircraft.parking_space = assigned_fato_resource
            aircraft.parking_space_id = assigned_fato_id  
            parking_space = assigned_fato_resource
            parking_space_id = assigned_fato_id

    def simulate_landing_process(self, aircraft: object):
        # Save FATO usage start time
        self.event_saver.update_fato_usage_tracker(vertiport_id=aircraft.destination_vertiport_id,
                                                   fato_usage=1)
        
        # Landing process
        yield self.env.process(aircraft.aircraft_landing_process())

        # Release approach fix
        approach_fix = self.get_last_airlink_resource(flight_direction=aircraft.flight_direction)
        approach_fix.release(aircraft.arrival_fix_usage_request)
        aircraft.flight_direction = None

    def simulate_taxi_process(self, aircraft: object, operation_type: str):
        # Get the taxi route
        if operation_type == 'arrival':
            taxi_route, taxi_route_edges = self.get_taxi_instructions(
                vertiport_id=aircraft.destination_vertiport_id,
                assigned_fato_id=aircraft.assigned_fato_id,
                parking_space_id=aircraft.parking_space_id
            )
        elif operation_type == 'departure':
            taxi_route, taxi_route_edges = self.get_taxi_instructions(
                vertiport_id=aircraft.origin_vertiport_id,
                assigned_fato_id=aircraft.assigned_fato_id,
                parking_space_id=aircraft.parking_space_id
            )

        taxi_start_time = self.env.now

        # Taxi process
        yield self.env.process(
            aircraft.taxi(
                taxi_route=taxi_route,
                taxi_route_edges=taxi_route_edges,
                operation_type=operation_type)
        )
        taxi_end_time = self.env.now
        self.event_saver.save_aircraft_taxi_time(vertiport_id=aircraft.destination_vertiport_id,
                                                 aircraft_id=aircraft.tail_number, 
                                                 taxi_time=taxi_end_time-taxi_start_time)

    def aircraft_charging_process(self, aircraft: object):
        # Charge the aircraft
        yield self.env.process(
            aircraft.charge_aircraft(
                parking_space=aircraft.parking_space,
                shared_charger=self.vertiports[aircraft.destination_vertiport_id].shared_charger_sets
            )
        )

        # Take out the aircraft from active aircraft list and put it into available aircraft list
        # self.active_aircraft_store.get(lambda filt: filt == aircraft.tail_number)
        self.put_aircraft_into_available_aircraft_store(vertiport_id=aircraft.destination_vertiport_id, 
                                                        aircraft=aircraft)

        if self.only_aircraft_simulation and not self.network_simulation:
            yield self.env.process(
                self.simulate_aircraft_departure_process(aircraft=aircraft, origin_vertiport_id=aircraft.origin_vertiport_id, destination_vertiport_id=None)
            )

    def simulate_aircraft_departure_process(self, aircraft, origin_vertiport_id, destination_vertiport_id):
        aircraft.origin_vertiport_id = origin_vertiport_id
        aircraft.destination_vertiport_id = destination_vertiport_id
        aircraft.flight_direction = f'{origin_vertiport_id}_{destination_vertiport_id}'

        # Save passenger boarding time
        for passenger in aircraft.passengers_onboard:
            self.event_saver.save_agent_state(agent=passenger, agent_type='passenger', event='boarding')

        boarding_time = self.env.now

        yield self.env.process(self.fato_pad_request(aircraft=aircraft, operation_type='departure'))

        # Save passenger departure queue waiting time
        for passenger in aircraft.passengers_onboard:
            self.event_saver.save_passenger_departure_queue_waiting_time(
                vertiport_id=aircraft.origin_vertiport_id,
                passenger_id=passenger.passenger_id,
                boarding_time=boarding_time
            )

        if not self.only_aircraft_simulation and len(aircraft.passengers_onboard) > 0:
            # Decrease the passenger departure queue counter
            self.event_saver.update_passenger_departure_queue_counter(vertiport_id=aircraft.origin_vertiport_id,
                                                                      queue_update=-1)

        # Save FATO usage start time
        self.event_saver.update_fato_usage_tracker(vertiport_id=aircraft.origin_vertiport_id,
                                                   fato_usage=1)

        taxi_usage_request = self.request_taxi_resource(vertiport_id=aircraft.origin_vertiport_id)
        if taxi_usage_request is not None:
            yield taxi_usage_request

        # Save pushback time
        self.event_saver.save_agent_state(agent=aircraft, agent_type='aircraft', event='pushback') 
        self.event_saver.save_flight_info(origin_vertiport_id=aircraft.origin_vertiport_id,
                                          destination_vertiport_id=aircraft.destination_vertiport_id,
                                          tail_number=aircraft.tail_number,
                                          aircraft_pushback_time=self.env.now,
                                          passengers=get_passenger_ids_from_passenger_list(aircraft.passengers_onboard),
                                          aircraft_model=aircraft.aircraft_model,
                                          event_type='pushback')        

        # Save total transfer time of a passenger
        for passenger in aircraft.passengers_onboard:
            self.event_saver.save_passenger_transfer_time(vertiport_id=aircraft.origin_vertiport_id,
                                                          passenger_id=passenger.passenger_id,
                                                          transfer_time=self.env.now - passenger.vertiport_arrival_time)

        # Taxi-out process
        yield self.env.process(self.simulate_taxi_process(aircraft=aircraft, operation_type='departure'))

        
        yield self.env.process(self.departure_fix_request(aircraft=aircraft))

        self.release_taxi_usage_request(vertiport_id=aircraft.origin_vertiport_id,
                                        taxi_usage_request=taxi_usage_request)    
        
        # Take-off process
        yield self.env.process(
            aircraft.aircraft_take_off_process(
                take_off_fato_id=aircraft.assigned_fato_id
            )
        ) 

        self.update_flight_info(aircraft=aircraft)

        yield self.env.process(aircraft.fly_in_the_airspace())
        
    def update_flight_info(self, aircraft: object):
        self.event_saver.update_flight_tracker(vertiport_id=aircraft.origin_vertiport_id)
        self.event_saver.update_load_factor_tracker(vertiport_id=aircraft.origin_vertiport_id, 
                                                    load_factor=len(aircraft.passengers_onboard))
        
    def departure_fix_request(self, aircraft):
        # Request departure fix resource
        departure_fix_usage_request, departure_fix_resource = self.request_fix_resource(flight_direction=aircraft.flight_direction,
                                                                operation_type='departure')
        yield departure_fix_usage_request
        aircraft.departure_fix_usage_request = departure_fix_usage_request
        aircraft.departure_fix_resource = departure_fix_resource

    def departure_fix_request_initial_state(self, aircraft):
        # Request departure fix resource
        departure_fix_usage_request, departure_fix_resource = self.request_fix_resource(flight_direction=aircraft.flight_direction, 
                                                                operation_type='departure')
        yield departure_fix_usage_request
        aircraft.departure_fix_usage_request = departure_fix_usage_request
        aircraft.departure_fix_resource = departure_fix_resource

        yield self.env.process(aircraft.fly_in_the_airspace())

