import simpy
import networkx as nx
from typing import Any, Dict
from utils.units import sec_to_ms
from utils.distribution_generator import DistributionGenerator
from utils.helpers import get_passenger_ids_from_passenger_list, calculate_passenger_consolidation_time
from battery_model import BatteryModel
import pandas as pd
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
                 network_simulation: bool):
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
        # if not self.network_simulation:
        self.charging_time_distribution = self.build_charging_time_distribution()
        self.aircraft_battery_models = self.build_aircraft_battery_models()
        self.taxi_resource = simpy.Resource(self.env, 1)
        if not self.only_aircraft_simulation and self.max_flight_waiting_time is not False:
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

    def assign_fato(self, vertiport_id: Any, parking_space: str, rule: str = 'min') -> str:
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
                taxi_length = nx.dijkstra_path_length(self.vertiports[vertiport_id].vertiport_layout.G,
                                                      parking_space, fato.resource_id)
                available_fato_pads[fato.resource_id] = taxi_length

        # Find the key of shortest distance
        if rule == 'min':
            return min(available_fato_pads, key=available_fato_pads.get)
        else:
            return max(available_fato_pads, key=available_fato_pads.get)

    def request_fato(self, assigned_fato_resource: object, operation_type: str):
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

    def request_fix_resource(self, aircraft: object, operation_type: str):
        """
        Requests the fix resource from vertiport manager
        """
        if operation_type == 'arrival':
            arrival_fix_resource = self.vertiports[aircraft.arrival_vertiport_id].arrival_fix_resource
            return arrival_fix_resource.request()            
        elif operation_type == 'departure':
            departure_fix_resource = self.vertiports[aircraft.departure_vertiport_id].departure_fix_resource
            return departure_fix_resource.request()

    def release_fix_resource(self, aircraft: object, fix_resource_request: object, operation_type: str):
        """
        Releases the fix resource from usage
        """
        if operation_type == 'arrival':
            arrival_fix_resource = self.vertiports[aircraft.arrival_vertiport_id].arrival_fix_resource
            arrival_fix_resource.release(fix_resource_request)
        elif operation_type == 'departure':
            departure_fix_resource = self.vertiports[aircraft.departure_vertiport_id].departure_fix_resource
            departure_fix_resource.release(fix_resource_request)            

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

    def get_parking_pad(self, vertiport_id: Any) -> str:
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

    def get_mission_length(self, origin_vertiport_id: Any, dest_vertiport_id: Any) -> float:
        """
        Returns the mission length given the destination vertiport ID
        """
        return self.vertiport_distances[(self.vertiport_distances['origin_vertiport_id'] == origin_vertiport_id) & 
                                        (self.vertiport_distances['destination_vertiport_id'] == dest_vertiport_id)]['distance_miles'].values[0]

    def reserve_aircraft(self, origin_vertiport_id: Any, dest_vertiport_id: int, departing_passengers: list,):

        # Get the first available aircraft. # TODO: Implement optimized aircraft allocation algorithms
        aircraft = yield self.vertiports[origin_vertiport_id].available_aircraft_store.get()

        # After allocating an aircraft, checks the waiting room again. If there are newcomers add them to the flight
        # list
        if len(departing_passengers) < self.aircraft_params['pax'] and \
                len(departing_passengers[0].waiting_room_store.items) > 0:
            departing_passengers.extend(self.scheduler.last_call_check(
                current_waiting_room=departing_passengers[0].waiting_room_store,
                num_departing_passengers=len(departing_passengers)))

        # Save the aircraft allocation time
        self.event_saver.save_aircraft_allocation_time(vertiport_id=origin_vertiport_id,
                                                       parking_pad_id=aircraft.parking_space_id,
                                                       agent_id=aircraft.tail_number,
                                                       aircraft_model=aircraft.aircraft_model,
                                                       agent_type='aircraft')
    
        # Save the aircraft idle time
        self.event_saver.save_aircraft_idle_time(vertiport_id=origin_vertiport_id,
                                                 agent_id=aircraft.tail_number,
                                                 charging_end_time=aircraft.charging_end_time)
        
        # Save aircraft flight assignment time
        self.event_saver.save_aircraft_flight_assignment_time(vertiport_id=origin_vertiport_id,
                                                              parking_pad_id=aircraft.parking_space_id,
                                                              agent_id=aircraft.tail_number,
                                                              agent_type='aircraft',
                                                              aircraft_model=aircraft.aircraft_model)
    
        aircraft.passengers_onboard = departing_passengers
        

        # Save total passenger waiting time until the flight assignment
        for passenger in aircraft.passengers_onboard:
            self.event_saver.save_passenger_waiting_time(vertiport_id=origin_vertiport_id,
                                                         passenger_id=passenger.passenger_id,
                                                         waiting_time=self.env.now - passenger.waiting_room_arrival_time)

        # Save passenger-flight assignment time
        for passenger in aircraft.passengers_onboard:
            self.event_saver.save_passenger_flight_assignment_time(vertiport_id=origin_vertiport_id,
                                                                   passenger_id=passenger.passenger_id,
                                                                   agent_type='passenger')
        # self.event_saver.save_flight_info(tail_number=aircraft.tail_number,
        #                                   passengers=get_passenger_ids_from_passenger_list(departing_passengers),
        #                                   aircraft_model=aircraft.aircraft_model,
        #                                   event_type='flight_assignment')

        # Simulate aircraft departure process
        yield self.env.process(
            self.simulate_aircraft_departure_process(aircraft=aircraft, 
                                                     origin_vertiport_id=origin_vertiport_id, 
                                                     dest_vertiport_id=dest_vertiport_id)
        )

    def trigger_scheduler(self, origin_vertiport_id, dest_vertiport_id: int, passengers_waiting_room: simpy.Store):
        if departing_passengers := self.scheduler.check_waiting_room(current_waiting_room=passengers_waiting_room):
            # Save passenger group completion time
            for passenger in departing_passengers:
                self.event_saver.save_passenger_waiting_room_departure_time(agent_id=passenger.passenger_id,
                                                                            vertiport_id=origin_vertiport_id,
                                                                            waiting_room_id=dest_vertiport_id,
                                                                            agent_type='passenger')

            # Save passenger consolidation time
            self.event_saver.save_passenger_group_consolidation_time(
                vertiport_id=origin_vertiport_id,
                passenger_ids=get_passenger_ids_from_passenger_list(departing_passengers),
                wr_number=dest_vertiport_id,
                consolidation_time=calculate_passenger_consolidation_time(departing_passengers)
            )

            # Increase passenger queue count
            self.event_saver.update_passenger_departure_queue_counter(vertiport_id=origin_vertiport_id, queue_update=1)

            yield self.env.process(self.reserve_aircraft(origin_vertiport_id=origin_vertiport_id, 
                                                         dest_vertiport_id=dest_vertiport_id, 
                                                         departing_passengers=departing_passengers))

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
                # for departing_passengers in departing_passenger_groups:
                #     yield self.env.process(self.reserve_aircraft(departing_passengers))

                # Save passenger waiting room departure time
                for vertiport_id, departing_passengers in departing_passenger_groups.items():
                    for passenger in departing_passengers:
                        self.event_saver.save_passenger_waiting_room_departure_time(agent_id=passenger.passenger_id,
                                                                                    vertiport_id=vertiport_id,
                                                                                    waiting_room_id=passenger.dest_vertiport_id,
                                                                                    agent_type='passenger')
                    # Increase passenger queue count
                    self.event_saver.update_passenger_departure_queue_counter(vertiport_id=vertiport_id, 
                                                                              queue_update=len(departing_passenger_groups))

                    flight_queue = [self.env.process(
                        self.reserve_aircraft(origin_vertiport_id=vertiport_id, 
                                              dest_vertiport_id=passengers[0].dest_vertiport_id,
                                              departing_passengers=passengers))
                        for passengers
                        in departing_passengers]
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
        self.event_saver.save_passenger_waiting_room_arrival_time(vertiport_id=passenger.origin_vertiport_id,
                                                                  passenger_id=passenger.passenger_id,
                                                                  waiting_room_id=passenger.dest_vertiport_id)
        passenger.waiting_room_arrival_time = self.env.now

        passengers_waiting_room = self.vertiports[passenger.origin_vertiport_id].waiting_room_stores[
            f'waiting_room_{passenger.dest_vertiport_id}']
        passengers_waiting_room.put(passenger)
        passenger.waiting_room_store = passengers_waiting_room
        yield self.env.process(self.trigger_scheduler(origin_vertiport_id=passenger.origin_vertiport_id,
                                                      dest_vertiport_id=passenger.dest_vertiport_id, 
                                                      passengers_waiting_room=passengers_waiting_room))

    def simulate_passenger_arrival(self, passenger):
        """ Simulate passenger."""
        # Save passenger creation time
        self.event_saver.save_agent_creation_time(agent_id=passenger.passenger_id,
                                                  agent_type='passenger',
                                                  vertiport_id=passenger.origin_vertiport_id)
        passenger.vertiport_arrival_time = self.env.now

        # Simulate agent's walk from car to the vertiport entrance
        yield self.env.process(passenger.walk_to_entrance())
        # Save the time when the passenger arrives at the vertiport entrance
        self.event_saver.save_passenger_vertiport_entrance_arrival_time(vertiport_id=passenger.origin_vertiport_id,
                                                                        passenger_id=passenger.passenger_id)
        # Simulate agent's security check
        yield self.env.process(passenger.security_check())
        # Save the time when the passenger finishes the security check
        self.event_saver.save_passenger_security_check_finish_time(vertiport_id=passenger.origin_vertiport_id,
                                                                   passenger_id=passenger.passenger_id)
        # Put the passenger into the waiting room
        yield self.env.process(self.put_passenger_into_waiting_room(passenger))

    # def simulate_passenger_departure(self, departing_passengers):
    #     for passenger in departing_passengers:
    #         yield self.env.process(passenger.waiting_room_to_boarding_gate())
    #         self.event_saver.save_passenger_boarding_gate_arrival_time(agent_id=passenger.passenger_id)

    def simulate_aircraft_arrival_process(self, aircraft, arriving_passengers=None):
        # TODO: keep track of arriving passengers

        # Increase aircraft arrival queue counter
        self.event_saver.update_aircraft_arrival_queue_counter(vertiport_id=aircraft.arrival_vertiport_id,
                                                               queue_update=1)
        
        # Request arrival fix resource
        arrival_fix_usage_request = self.request_fix_resource(aircraft=aircraft, operation_type='arrival')
        yield arrival_fix_usage_request

        # Save aircraft arrival time
        self.event_saver.save_pre_landing_info(agent_id=aircraft.tail_number, 
                                               aircraft_model=aircraft.aircraft_model,
                                               vertiport_id=aircraft.arrival_vertiport_id,
                                               agent_type='aircraft')
        
        self.release_fix_resource(aircraft=aircraft,
                                  fix_resource_request=arrival_fix_usage_request, 
                                  operation_type='arrival')

        if self.vertiports[aircraft.arrival_vertiport_id].vertiport_layout.num_parking_pad > 0:
            # parking space reservation for landing
            parking_space = yield self.get_parking_pad(vertiport_id=aircraft.arrival_vertiport_id)
            parking_space_id = parking_space.resource_id
            # Save them to use for departure
            aircraft.parking_space = parking_space
            aircraft.parking_space_id = parking_space_id   
        else:
            parking_space = None
            parking_space_id = None   

        # Currently, vertiport manager assigns the closest FATO
        assigned_fato_id = self.assign_fato(vertiport_id=aircraft.arrival_vertiport_id,
                                            parking_space=parking_space_id)

        # Aircraft calls the FATO resource that will be requested.
        assigned_fato_resource = self.call_fato_resource(vertiport_id=aircraft.arrival_vertiport_id,
                                                         assigned_fato_id=assigned_fato_id)
        
        # If there is no parking pad then aircraft will be parked on FATO
        if self.vertiports[aircraft.arrival_vertiport_id].vertiport_layout.num_parking_pad == 0:
            aircraft.parking_space = assigned_fato_resource
            aircraft.parking_space_id = assigned_fato_id  
            parking_space = assigned_fato_resource
            parking_space_id = assigned_fato_id            


        # Request for FATO pad usage
        aircraft_fato_usage_request = self.request_fato(
            assigned_fato_resource=assigned_fato_resource,
            operation_type='arrival'
        )
        yield aircraft_fato_usage_request

        # Save aircraft arrival queue waiting time
        self.event_saver.save_aircraft_arrival_queue_waiting_time(vertiport_id=aircraft.arrival_vertiport_id,
                                                                  agent_id=aircraft.tail_number,
                                                                  waiting_time=self.env.now - aircraft.arrival_time)
        
        aircraft.holding_time = self.env.now - aircraft.arrival_time

        # Save FATO usage start time
        self.event_saver.update_fato_usage_tracker(vertiport_id=aircraft.arrival_vertiport_id,
                                                   fato_usage=1)

        # Landing process
        yield self.env.process(aircraft.aircraft_landing_process(landing_fato_id=assigned_fato_id))

        # Get the taxi route
        taxi_route, taxi_route_edges = self.get_taxi_instructions(
            vertiport_id=aircraft.arrival_vertiport_id,
            assigned_fato_id=assigned_fato_id,
            parking_space_id=parking_space_id
        )

        taxi_start_time = self.env.now
        # Taxi-in process
        yield self.env.process(
            aircraft.taxi(
                taxi_route=taxi_route,
                taxi_route_edges=taxi_route_edges,
                assigned_fato_resource=assigned_fato_resource,
                parking_space_id=parking_space_id,
                parking_space=parking_space,
                aircraft_fato_usage_request=aircraft_fato_usage_request,
                operation_type='arrival')
        )
        taxi_end_time = self.env.now
        self.event_saver.save_aircraft_taxi_time(vertiport_id=aircraft.arrival_vertiport_id,
                                                 aircraft_id=aircraft.tail_number, 
                                                 taxi_time=taxi_end_time-taxi_start_time)

        # Charge the aircraft
        yield self.env.process(
            aircraft.charge_aircraft(
                parking_space=parking_space,
                shared_charger=self.vertiports[aircraft.arrival_vertiport_id].shared_charger_sets
            )
        )

        # Take out the aircraft from active aircraft list and put it into available aircraft list
        # self.active_aircraft_store.get(lambda filt: filt == aircraft.tail_number)
        self.put_aircraft_into_available_aircraft_store(vertiport_id=aircraft.arrival_vertiport_id, 
                                                        aircraft=aircraft)

        if self.only_aircraft_simulation and not self.network_simulation:
            yield self.env.process(
                self.simulate_aircraft_departure_process(aircraft=aircraft, departing_passengers=[])
            )

    def simulate_aircraft_departure_process(self, aircraft, origin_vertiport_id, dest_vertiport_id):
        aircraft.departure_vertiport_id = origin_vertiport_id
        aircraft.arrival_vertiport_id = dest_vertiport_id
        # Save passenger boarding time
        for passenger in aircraft.passengers_onboard:
            self.event_saver.save_passenger_boarding_finish_time(passenger_id=passenger.passenger_id,
                                                                 aircraft=aircraft,
                                                                 vertiport_id=origin_vertiport_id)

        boarding_time = self.env.now    
        
        # Aircraft take off request
        assigned_fato_id = self.assign_fato(vertiport_id=aircraft.departure_vertiport_id, 
                                            parking_space=aircraft.parking_space_id)

        # Aircraft calls the FATO resource that will be requested.
        assigned_fato_resource = self.call_fato_resource(vertiport_id=aircraft.departure_vertiport_id,
                                                         assigned_fato_id=assigned_fato_id)

        # Increase the aircraft departure queue counter
        self.event_saver.update_aircraft_departure_queue_counter(vertiport_id=aircraft.departure_vertiport_id,
                                                                 queue_update=1)

        # Request for FATO pad usage
        aircraft_fato_usage_request = self.request_fato(
            assigned_fato_resource=assigned_fato_resource,
            operation_type='departure'
        )
        yield aircraft_fato_usage_request

        # Save passenger departure queue waiting time
        for passenger in aircraft.passengers_onboard:
            self.event_saver.save_passenger_departure_queue_waiting_time(
                vertiport_id=aircraft.departure_vertiport_id,
                passenger_id=passenger.passenger_id,
                boarding_time=boarding_time
            )

        # Decrease the aircraft departure queue counter
        self.event_saver.update_aircraft_departure_queue_counter(vertiport_id=aircraft.departure_vertiport_id,
                                                                 queue_update=-1)

        if not self.only_aircraft_simulation:
            # Decrease the passenger departure queue counter
            self.event_saver.update_passenger_departure_queue_counter(vertiport_id=aircraft.departure_vertiport_id,
                                                                      queue_update=-1)

        # Save FATO usage start time
        self.event_saver.update_fato_usage_tracker(vertiport_id=aircraft.departure_vertiport_id,
                                                   fato_usage=1)

        taxi_usage_request = self.request_taxi_resource(vertiport_id=aircraft.departure_vertiport_id)
        if taxi_usage_request is not None:
            yield taxi_usage_request

        # Save pushback time
        self.event_saver.save_pushback_info(
            pushback_location=aircraft.parking_space_id,
            agent_id=aircraft.tail_number,
            aircraft_model=aircraft.aircraft_model,
            vertiport_id=aircraft.departure_vertiport_id
        )

        # Save total transfer time of a passenger
        for passenger in aircraft.passengers_onboard:
            self.event_saver.save_passenger_transfer_time(vertiport_id=aircraft.departure_vertiport_id,
                                                          passenger_id=passenger.passenger_id,
                                                          transfer_time=self.env.now - passenger.vertiport_arrival_time)

        taxi_start_time = self.env.now
        # Taxi-out process
        taxi_route, taxi_route_edges = self.get_taxi_instructions(vertiport_id=aircraft.departure_vertiport_id,
                                                                  parking_space_id=aircraft.parking_space_id, 
                                                                  assigned_fato_id=assigned_fato_id)
        yield self.env.process(
            aircraft.taxi(
                taxi_route=taxi_route,
                taxi_route_edges=taxi_route_edges,
                assigned_fato_resource=assigned_fato_resource,
                parking_space_id=aircraft.parking_space_id,
                parking_space=aircraft.parking_space,
                aircraft_fato_usage_request=aircraft_fato_usage_request,
                operation_type='departure')
        )
        taxi_end_time = self.env.now
        self.event_saver.save_aircraft_taxi_time(vertiport_id=aircraft.departure_vertiport_id, 
                                                 aircraft_id=aircraft.tail_number, 
                                                 taxi_time=taxi_end_time-taxi_start_time)

        # Save take-off info
        self.event_saver.save_flight_info(origin_vertiport_id=aircraft.departure_vertiport_id,
                                          destination_vertiport_id=aircraft.arrival_vertiport_id,
                                          tail_number=aircraft.tail_number,
                                          passengers=get_passenger_ids_from_passenger_list(aircraft.passengers_onboard),
                                          aircraft_model=aircraft.aircraft_model,
                                          event_type='take_off')

        # Request departure fix resource
        departure_fix_usage_request = self.request_fix_resource(aircraft=aircraft, 
                                                                operation_type='departure')
        yield departure_fix_usage_request

        # Take-off process
        yield self.env.process(
            aircraft.aircraft_take_off_process(
                take_off_fato_id=assigned_fato_id,
                departure_fix_usage_request=departure_fix_usage_request
            )
        )

        self.release_taxi_usage_request(vertiport_id=aircraft.departure_vertiport_id,
                                        taxi_usage_request=taxi_usage_request)
        # Release the FATO
        assigned_fato_resource.fato_resource.release(aircraft_fato_usage_request)

        # Save FATO usage finish time
        self.event_saver.update_fato_usage_tracker(vertiport_id=aircraft.departure_vertiport_id,
                                                   fato_usage=-1)
        
        flight_direction = aircraft.departure_vertiport_id + '_' + aircraft.arrival_vertiport_id
        yield self.env.process(aircraft.fly_in_the_airspace(flight_direction=flight_direction))
        

    def reroute_aircraft(self):
        pass

