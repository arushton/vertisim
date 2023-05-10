from utils.helpers import timestamp_to_datetime, get_key_from_value
from utils.units import sec_to_ms, min_to_sec, ms_to_sec, hr_to_ms
from typing import Union, Dict, List, Optional
import pandas as pd # For type hinting
import numpy as np
import random


class Aircraft:
    """
    Aircraft agent
    """

    def __init__(self, env, tail_number, arrival_vertiport_id, battery_capacity, ground_taxi_speed, initial_soc, arrival_time, aircraft_model,
                 passenger_capacity, max_range,
                 time_charging,
                 time_passenger_embark_disembark, time_descend_transition, time_hover_descend, time_rotor_spin_down,
                 time_post_landing_safety_checks, time_tug_connection, time_pre_charging_processes,
                 time_charging_plug_disconnection, time_post_charging_processes, time_pre_take_off_check_list,
                 time_rotor_spin_up, time_hover_climb, time_climb_transition, time_tug_disconnection,
                 vertiport_manager, event_saver):
        self.env = env
        self.tail_number = tail_number
        self.aircraft_model = aircraft_model
        self.battery_capacity = battery_capacity
        self.passenger_capacity = passenger_capacity
        self.max_range = max_range
        self.ground_taxi_speed = ground_taxi_speed
        self.initial_soc = initial_soc
        self.current_soc = initial_soc
        self.arrival_time = arrival_time # TODO: Update this at every holding fix arrival
        self.arrival_vertiport_id = arrival_vertiport_id   
        self.departure_vertiport_id = None             
        self.charging_start_time = None
        self.charging_end_time = None
        self.parking_space = None
        self.parking_space_id = None
        self.holding_time = None # event_saver.aircraft_arrival_queue_waiting_time keeps track of this for every aircraft at every vertiport


        self.time_passenger_embark_disembark = time_passenger_embark_disembark

        self.time_descend_transition = time_descend_transition
        self.time_hover_descend = time_hover_descend
        self.time_rotor_spin_down = time_rotor_spin_down
        self.time_post_landing_safety_checks = time_post_landing_safety_checks
        self.time_tug_connection = time_tug_connection
        self.time_tug_disconnection = time_tug_disconnection

        self.time_pre_charging_processes = time_pre_charging_processes
        self.time_charging = time_charging
        self.time_charging_plug_disconnection = time_charging_plug_disconnection
        self.time_post_charging_processes = time_post_charging_processes

        self.time_pre_take_off_check_list = time_pre_take_off_check_list
        self.time_rotor_spin_up = time_rotor_spin_up
        self.time_hover_climb = time_hover_climb
        self.time_climb_transition = time_climb_transition
        self.vertiport_manager = vertiport_manager
        self.event_saver = event_saver

    def aircraft_landing_process(self, time_descend_transition, time_hover_descend, time_rotor_spin_down,
                                 landing_fato_id, time_post_landing_safety_checks, time_tug_connection):

        yield self.env.timeout(time_descend_transition)
        yield self.env.timeout(time_hover_descend)
        self.event_saver.save_landing_info(assigned_fato_id=landing_fato_id,
                                           agent_id=self.tail_number,
                                           aircraft_model=self.aircraft_model,
                                           vertiport_id=self.arrival_vertiport_id)
        yield self.env.timeout(time_rotor_spin_down)
        yield self.env.timeout(time_post_landing_safety_checks)
        yield self.env.timeout(time_tug_connection)
        # Save landing information
        self.event_saver.save_landing_time(assigned_fato_id=landing_fato_id,
                                           agent_id=self.tail_number,
                                           aircraft_model=self.aircraft_model,
                                           vertiport_id=self.arrival_vertiport_id)

    def taxi(self, 
             taxi_route: list, 
             taxi_route_edges: list, 
             assigned_fato_resource: object, 
             parking_space_id: str,
             parking_space, 
             aircraft_fato_usage_request: object, 
             operation_type: str,
             departing_passengers: Union[List, None]) -> None:
        """
        Simulates aircraft taxi. It doesn't matter whether it is taxi-in or
        taxi-out. Vertiport manager provides the taxi route as a list. The
        first and the last node in the taxi route list will be a parking space
        ID and a FATO pad ID. Algorithm first reserves all of the nodes and
        edges in the taxi route. As the aircraft passes these nodes and edges
        algorithm puts back these nodes and edges to taxiway_node_store and
        edge_store of the vertiport manager.

        Example taxi_route for take-off
        ['PS13', 'PS12_PS13', 'PS11_PS12', 'TLOF1']

        Example taxi_route_edges for take-off
        ['PS13__PS12_PS13', 'PS12_PS13__PS11_PS12', 'PS11_PS12__TLOF1']

        Parameters
        ----------
        taxi_route : list
            list of nodes that an aircraft has to follow for its taxi
        taxi_route_edges : list
            list of edges that an aircraft has to follow for its taxi
        assigned_fato_resource : object
            Instance of the fato resource that is assigned to the aircraft
        parking_space_id : str
            id of the assigned parking space
        aircraft_fato_usage_request : object
            FATO pad request object that needs to be released.
        operation_type : str
            It can be only 'arrival' or 'departure'
         departing_passengers : List or None
        """
        if operation_type == 'arrival':
            vertiport_id = self.arrival_vertiport_id
        elif operation_type == 'departure':
            vertiport_id = self.departure_vertiport_id
        # Check whether the vertiport has a parking pad or not. If it has a parking pad then the aircraft will taxi. Otherwise, it will be parked on the FATO pad.
        if len(taxi_route) == 0:
            if operation_type == 'arrival':
                # Decrease the aircraft arrival queue counter
                self.event_saver.update_aircraft_arrival_queue_counter(vertiport_id=vertiport_id,
                                                                       queue_update=-1)     
                self.event_saver.save_parking_info(parking_pad_id=assigned_fato_resource.resource_id,
                                                   agent_id=self.tail_number,
                                                   aircraft_model=self.aircraft_model,
                                                   vertiport_id=vertiport_id)
            return                          

        # Get the first node and the last node on the taxi route. They are
        # parking space nodes or FATO pad nodes. Since they are already assigned
        # no need to reserve them.
        first_node = taxi_route.pop(0)
        last_node = taxi_route.pop(-1)

        # Reserve all of the taxiway edges
        taxiway_edges = []
        for edge in taxi_route_edges:
            taxiway_edge = yield self.vertiport_manager.vertiports[vertiport_id].edge_store.get(lambda filt: filt == edge)
            taxiway_edges.append(taxiway_edge)

        if len(taxi_route) == 0:
            # Case that the FATO pad and parking space directly connected
            if operation_type == 'arrival':
                # Release the TLOF pad resource after reaching to the parking space
                assigned_fato_resource.fato_resource.release(aircraft_fato_usage_request)

                # Save FATO usage finish time
                self.event_saver.update_fato_usage_tracker(vertiport_id=vertiport_id,
                                                           fato_usage=-1)

                # Decrease the aircraft arrival queue counter
                self.event_saver.update_aircraft_arrival_queue_counter(vertiport_id=vertiport_id,
                                                                       queue_update=-1)
                
            # Put back the only edge on the taxi route
            self.vertiport_manager.vertiports[vertiport_id].edge_store.put(taxiway_edges.pop(0))
            if operation_type == 'departure':
                # Release the parking space of the departing aircraft. FATO nodes handled by the vertiport manager.
                self.vertiport_manager.release_parking_space(vertiport_id=vertiport_id,
                                                             departure_parking_space=parking_space)

            node_to_node_move_time = int(round(self.vertiport_manager.vertiports[vertiport_id].vertiport_layout.
                                               node_distances.loc[
                                                   first_node, last_node] / self.ground_taxi_speed * 1000))
            yield self.env.timeout(node_to_node_move_time)

            # Save park time
            if operation_type == 'arrival':
                self.event_saver.save_parking_info(parking_pad_id=parking_space_id,
                                                   agent_id=self.tail_number,
                                                   aircraft_model=self.aircraft_model,
                                                   vertiport_id=vertiport_id)

        else:
            # Reserve all of the taxiway nodes
            taxiway_nodes = []
            for node in taxi_route:
                taxiway_node = yield self.vertiport_manager.vertiports[vertiport_id].taxiway_node_store.get(
                    lambda filt: filt == node)
                taxiway_nodes.append(taxiway_node)

            next_node = taxi_route.pop(0)
            # Move from first node to the next node over an edge
            node_to_node_move_time = int(round(self.vertiport_manager.vertiports[vertiport_id].vertiport_layout.
                                               node_distances.loc[
                                                   first_node, next_node] / self.ground_taxi_speed * 1000))
            yield self.env.timeout(node_to_node_move_time)

            # Save the location and time of the current node
            self.event_saver.save_taxi_location_time_info(
                node=next_node,
                agent_id=self.tail_number,
                agent_type='aircraft',
                aircraft_model=self.aircraft_model,
                vertiport_id=vertiport_id)

            previous_node = next_node

            if operation_type == 'arrival':
                # Release the FATO pad resource after reaching to the nextNode
                assigned_fato_resource.fato_resource.release(aircraft_fato_usage_request)

                # Save FATO usage finish time
                self.event_saver.update_fato_usage_tracker(vertiport_id=vertiport_id,
                                                           fato_usage=-1)

                # Decrease the aircraft arrival queue counter
                self.event_saver.update_aircraft_arrival_queue_counter(vertiport_id=vertiport_id,
                                                                       queue_update=-1)

            if operation_type == 'departure':
                # Release the parking space of the departing aircraft
                self.vertiport_manager.release_parking_space(vertiport_id=vertiport_id,
                                                             departure_parking_space=parking_space)

            # Put back the passed edge between the first node and the next node
            # Don't need to put back the first and last node because they are
            # handled by the vertiport manager.
            self.vertiport_manager.vertiports[vertiport_id].edge_store.put(taxiway_edges.pop(0))

            for idx, node in enumerate(taxi_route):
                # Move between taxi nodes over taxi edges
                node_to_node_move_time = int(round(self.vertiport_manager.vertiports[vertiport_id].vertiport_layout.node_distances.
                                                   loc[previous_node, node] / self.ground_taxi_speed * 1000))
                yield self.env.timeout(node_to_node_move_time)

                # Save the location and time of the current node
                self.event_saver.save_location_time_info(
                    node=next_node,
                    agent_id=self.tail_number,
                    agent_type='aircraft',
                    aircraft_model=self.aircraft_model,
                    vertiport_id=vertiport_id)
                
                if operation_type == 'departure':
                    # Save passenger location and time
                    for passenger in departing_passengers:
                        self.event_saver.save_taxi_location_time_info(
                            node=next_node,
                            agent_id=passenger.passenger_id,
                            agent_type='passenger',
                            aircraft_model=None,
                            vertiport_id=vertiport_id)

                # Put back the previous node and edge
                self.vertiport_manager.vertiports[vertiport_id].taxiway_node_store.put(previous_node)
                self.vertiport_manager.vertiports[vertiport_id].edge_store.put(taxiway_edges.pop(0))
                previous_node = node

            node_to_node_move_time = int(round(self.vertiport_manager.vertiports[vertiport_id].vertiport_layout.node_distances.loc[
                                                   previous_node, last_node] / self.ground_taxi_speed * 1000))
            yield self.env.timeout(node_to_node_move_time)

            # Save park time
            if operation_type == 'arrival':
                self.event_saver.save_parking_info(parking_pad_id=parking_space_id,
                                                   agent_id=self.tail_number,
                                                   aircraft_model=self.aircraft_model,
                                                   vertiport_id=vertiport_id)

            # Put back the previous node and edge
            self.vertiport_manager.vertiports[vertiport_id].taxiway_node_store.put(previous_node)
            self.vertiport_manager.vertiports[vertiport_id].edge_store.put(taxiway_edges.pop(0))

    def aircraft_take_off_process(self, time_rotor_spin_up, time_hover_climb, time_climb_transition, take_off_fato_id,
                                  time_pre_take_off_check_list, time_tug_disconnection, departing_passengers,
                                  departure_fix_usage_request):
        self.event_saver.save_fato_arrival_info(assigned_fato_id=take_off_fato_id,
                                                agent_id=self.tail_number,
                                                agent_type='aircraft',
                                                aircraft_model=self.aircraft_model,
                                                vertiport_id=self.departure_vertiport_id)

        # Save passenger location and time
        for passenger in departing_passengers:
            self.event_saver.save_fato_arrival_info(assigned_fato_id=take_off_fato_id,
                                                    agent_id=passenger.passenger_id,
                                                    agent_type='passenger',
                                                    aircraft_model=None,
                                                    vertiport_id=self.departure_vertiport_id)

        yield self.env.timeout(time_tug_disconnection)
        yield self.env.timeout(time_pre_take_off_check_list)
        yield self.env.timeout(time_rotor_spin_up)
        self.event_saver.save_take_off_info(assigned_fato_id=take_off_fato_id,
                                            agent_id=self.tail_number,
                                            agent_type='aircraft',
                                            aircraft_model=self.aircraft_model,
                                            vertiport_id=self.departure_vertiport_id)
        # Save passenger location and time
        for passenger in departing_passengers:
            self.event_saver.save_take_off_info(assigned_fato_id=take_off_fato_id,
                                                agent_id=passenger.passenger_id,
                                                agent_type='passenger',
                                                aircraft_model=None,
                                                vertiport_id=self.departure_vertiport_id)
        yield self.env.timeout(time_hover_climb)
        yield self.env.timeout(time_climb_transition)
        self.event_saver.save_departure_fix_info(take_off_fato_id=take_off_fato_id,
                                                 agent_id=self.tail_number,
                                                 agent_type='aircraft',
                                                 aircraft_model=self.aircraft_model,
                                                 vertiport_id=self.departure_vertiport_id)
        # Save passenger location and time
        for passenger in departing_passengers:
            self.event_saver.save_departure_fix_info(take_off_fato_id=take_off_fato_id,
                                                     agent_id=passenger.passenger_id,
                                                     agent_type='passenger',
                                                     aircraft_model=None,
                                                     vertiport_id=self.departure_vertiport_id)
        
        # Release the departure fix
        self.vertiport_manager.release_fix_resource(aircraft=self,
                                                    fix_resource_request=departure_fix_usage_request,
                                                    operation_type='departure')

    def request_charger(self):
        """
        This method is used when the charger configuration is normal (any parking pads can use any chargers).
        """
        return self.vertiport_manager.vertiports[self.arrival_vertiport_id].charger_resource.request()

    def get_charging_time(self):
        """
        Get charging time - Two options: Constant charging time or draw a number from distribution
        """
        if self.time_charging is not None:
            return max(self.time_passenger_embark_disembark, self.time_charging)
        charge_time = sec_to_ms(self.vertiport_manager.charging_time_distribution.pick_number_from_distribution())
        charge_time = max(self.time_passenger_embark_disembark, charge_time)
        self.event_saver.save_aircraft_charging_time(vertiport_id=self.arrival_vertiport_id,
                                                     aircraft_id=self.tail_number, 
                                                     charging_time=charge_time)
        return charge_time

    def charge_aircraft(self, charge_time: float, parking_space: object,
                        time_pre_charging_processes: int, time_post_charging_processes: int,
                        time_charging_plug_disconnection: int, shared_charger: bool = False) -> None:
        """
        If the charger configuration is fixed and share-limited, all of the chargers that a parking pad has access
        should be requested. We use chargers as a resource instead of simpy.Store or simpy.Filterstore because it's
        easier to follow which resource is being used by which aircraft.
        """
        time_before_charger_allocation = self.env.now

        # If the chargers are shared, request all of the chargers that the parking pad has access to.
        if shared_charger:
            # Request all of the chargers that the parking pad has access.
            charger_requests = {charger: charger.request() for charger in parking_space.charger_resources}
            # Yield all of the charger requests. When any_of used it fires all of the requests.
            charging_request = yield self.env.any_of(list(charger_requests.values()))
            charging_requests_list = list(charging_request.keys())
            # The selected charging request is the on top of the list
            selected_charging_request = charging_requests_list[0]
            # Find which charger request is being used
            used_charger_resource = get_key_from_value(charger_requests, selected_charging_request)

            # Since any_of() used more than one request might be filled. Only one should be kept and the rest should
            # be canceled.
            for charger_res, charger_req in charger_requests.items():
                if charger_res != used_charger_resource:
                    if len(charging_requests_list) > 1:
                        charger_res.release(charger_req)
                    else:
                        charger_req.cancel()
        else:
            # If fixed and share-limited charger is not used
            charging_request = self.request_charger()
            yield charging_request

        self.event_saver.save_charging_start_time(charging_location=parking_space.resource_id,
                                                  agent_id=self.tail_number,
                                                  event='charging_started',
                                                  aircraft_model=self.aircraft_model,
                                                  vertiport_id=self.arrival_vertiport_id)
        self.charging_start_time = self.env.now

        # Actual charging happens here
        yield self.env.timeout(self.get_charging_time())
        self.charging_end_time = self.env.now

        # Update the SOC
        self.update_charge_level(operation='charge')

        self.event_saver.save_charging_finish_time(charging_location=parking_space.resource_id,
                                                   agent_id=self.tail_number,
                                                   event='charging_finished',
                                                   aircraft_model=self.aircraft_model,
                                                   vertiport_id=self.arrival_vertiport_id)

        if shared_charger:
            used_charger_resource.release(selected_charging_request)
        else:
            self.vertiport_manager.vertiports[self.arrival_vertiport_id].charger_resource.release(charging_request)

        self.event_saver.save_turnaround_info(charging_location=parking_space.resource_id,
                                              agent_id=self.tail_number,
                                              agent_type='aircraft',
                                              aircraft_model=self.aircraft_model,
                                              vertiport_id=self.arrival_vertiport_id,)

    @staticmethod
    def calc_soc_from_charge_time(charge_time: int, initial_soc: int, df: pd.DataFrame) -> int:
        """
        charge_time is the time between the current time and the charging start time.

        Parameters
        ----------
        charge_time: int
            Time between the current time and the charging start time in miliseconds.
        initial_soc: int
            Initial soc level of the aircraft.
        df: pd.DataFrame
            Dataframe that contains the soc levels and the time information.

        Returns
        -------
        int
            The soc level of the aircraft after the charging time.
        """
        # Calculate new soc from charge time
        # Get the time at initial soc level
        initial_soc_time = df[df.soc == initial_soc]['time_sec'].values[0]
        # Get the time at final soc level
        final_soc_time = initial_soc_time + ms_to_sec(charge_time)
        # Get the soc at final soc level
        idx_final_soc = df['time'].sub(final_soc_time).abs().idxmin()
        return df.loc[idx_final_soc]['soc']


    def update_charge_level(self, new_soc: int = None, operation: str = 'charge') -> None:
        """
        Updates the charge level of the aircraft using current charge time.
        """
        if operation == 'charge':
            charge_time = self.env.now - self.charging_start_time
            charge_lookup_table = self.vertiport_manager.aircraft_battery_models[self.arrival_vertiport_id]
            final_soc = Aircraft.calc_soc_from_charge_time(charge_time=charge_time, initial_soc=self.initial_soc, df=charge_lookup_table)
            self.current_soc = min(100, final_soc)
        elif operation == 'discharge':
            self.current_soc = new_soc

    def check_charge_level(self):
        return self.current_soc

    def unload_passengers(self, passenger_disembark_time):
        # TODO: check
        yield self.env.timeout(passenger_disembark_time)
        self.event_saver.aircraft_dict[self.tail_number]['passenger_unloading_finished'] = \
            timestamp_to_datetime(self.event_saver.sim_start_timestamp, self.env.now)
    
    def fly_in_the_airspace(self, flight_direction):
        link_traversal_time = hr_to_ms(self.vertiport.airspace.airlink_length / self.cruise_speed)
        for resource in self.vertiport.airspace.airlink_resources[flight_direction]:
            with resource.request() as req:
                yield req
                yield self.env.timeout(link_traversal_time)
            self.event_saver.

    # @staticmethod
    # def request_fato(assigned_fato_resource: object, priority: int) -> object:
    #     """
    #     Requests the assigned TLOF pad for an aircraft

    #     Parameters
    #     ----------
    #     assigned_fato_resource : object
    #         Class object that provides the FATO resource by request.
    #     priority : int
    #         Priority for using the FATO pad resource. Lower value prioritized

    #     Returns
    #     -------
    #     Request object
    #         FATO usage request
    #     """
    #     return assigned_fato_resource.fato_resource.request(priority=priority)

    # def call_fato_resource(self, assigned_fato_id: str) -> object:
    #     """
    #     Calls the assigned fato pad resource from fato_store of vertiport manager

    #     Parameters
    #     ----------
    #     assigned_fato_id : str
    #         Assigned TLOF pad ID by the vertiport manager.
    #     priority : int
    #         Priority for using the TLOF pad resource. Lower value prioritized

    #     Returns
    #     -------
    #     FatoResource class
    #         Class object that provides the FATO resource by request.
    #     """
    #     fato_list = [fato.fato_id for fato in self.vertiport_manager.vertiports[self.arrival_vertiport_id].fato_store.items]
    #     fato_index = fato_list.index(assigned_fato_id)
    #     return self.vertiport_manager.vertiports[self.arrival_vertiport_id].fato_store.items[fato_index]

    # def get_taxi_instructions(self, assigned_fato_id, parking_space_id):
    #     # Get the taxi route nodes from vertiport manager
    #     taxi_route, _ = self.vertiport_manager.generate_taxi_route_nodes(
    #         self.arrival_vertiport_id, assigned_fato_id, parking_space_id)

    #     # Get the taxi route edges from vertiport manager
    #     taxi_route_edges = self.vertiport_manager.generate_taxi_route_edges(taxi_route)
    #     return taxi_route, taxi_route_edges