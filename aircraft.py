from utils.helpers import timestamp_to_datetime, get_key_from_value
from utils.units import sec_to_ms, min_to_sec
from typing import Union, Dict, List, Optional
import numpy as np
import random


class Aircraft:
    """
    Aircraft agent
    """

    def __init__(self, env, tail_number, ground_taxi_speed, initial_soc, aircraft_model, aircraft_specs,
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
        self.aircraft_specs = aircraft_specs
        self.passenger_capacity = passenger_capacity
        self.max_range = max_range
        self.ground_taxi_speed = ground_taxi_speed
        self.initial_soc = initial_soc
        self.current_soc = initial_soc
        self.battery_capacity = None  # TODO: Use
        self.charging_start_time = None
        self.parking_space = None
        self.parking_space_id = None

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

        self.event_saver.save_pre_landing_info(landing_fato_id=landing_fato_id,
                                               agent_id=self.tail_number,
                                               aircraft_model=self.aircraft_model)
        yield self.env.timeout(time_descend_transition)
        yield self.env.timeout(time_hover_descend)
        self.event_saver.save_landing_info(assigned_fato_id=landing_fato_id,
                                           agent_id=self.tail_number,
                                           aircraft_model=self.aircraft_model)
        yield self.env.timeout(time_rotor_spin_down)
        yield self.env.timeout(time_post_landing_safety_checks)
        yield self.env.timeout(time_tug_connection)
        # Save landing information
        self.event_saver.save_landing_time(assigned_fato_id=landing_fato_id,
                                           agent_id=self.tail_number,
                                           aircraft_model=self.aircraft_model)

    @staticmethod
    def request_fato(assigned_fato_resource: object, priority: int) -> object:
        """
        Requests the assigned TLOF pad for an aircraft

        Parameters
        ----------
        assigned_fato_resource : object
            Class object that provides the FATO resource by request.
        priority : int
            Priority for using the FATO pad resource. Lower value prioritized

        Returns
        -------
        Request object
            FATO usage request
        """
        return assigned_fato_resource.fato_resource.request(priority=priority)

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
        fato_list = [fato.fato_id for fato in self.vertiport_manager.vertiport.fato_store.items]
        fato_index = fato_list.index(assigned_fato_id)
        return self.vertiport_manager.vertiport.fato_store.items[fato_index]

    def taxi(self, taxi_route: list, taxi_route_edges: list, assigned_fato_resource: object, parking_space_id: str,
             parking_space, aircraft_fato_usage_request: object, operation_type: str,
             departing_passengers: Union[List, None]) -> None:
        """
        Simulates aircraft taxi. It doesn't matter whether it is taxi-in or
        taxi-out. Skyport manager provides the taxi route as a list. The
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
        # Get the first node and the last node on the taxi route. They are
        # parking space nodes or FATO pad nodes. Since they are already assigned
        # no need to reserve them.
        first_node = taxi_route.pop(0)
        last_node = taxi_route.pop(-1)

        # Reserve all of the taxiway edges
        taxiway_edges = []
        for edge in taxi_route_edges:
            taxiway_edge = yield self.vertiport_manager.vertiport.edge_store.get(lambda filt: filt == edge)
            taxiway_edges.append(taxiway_edge)

        if len(taxi_route) == 0:
            # Case that the FATO pad and parking space directly connected
            if operation_type == 'arrival':
                # Release the TLOF pad resource after reaching to the parking space
                assigned_fato_resource.fato_resource.release(aircraft_fato_usage_request)

                # Decrease the aircraft arrival queue counter
                self.event_saver.update_aircraft_arrival_queue_counter(queue_update=-1)
                
            # Put back the only edge on the taxi route
            self.vertiport_manager.vertiport.edge_store.put(taxiway_edges.pop(0))
            if operation_type == 'departure':
                # Release the parking space of the departing aircraft. FATO nodes handled by the vertiport manager.
                self.vertiport_manager.release_parking_space(parking_space)

            node_to_node_move_time = int(round(self.vertiport_manager.vertiport.vertiport_layout.
                                               node_distances.loc[
                                                   first_node, last_node] / self.ground_taxi_speed * 1000))
            yield self.env.timeout(node_to_node_move_time)

            # Save park time
            if operation_type == 'arrival':
                self.event_saver.save_parking_info(parking_pad_id=parking_space_id,
                                                   agent_id=self.tail_number,
                                                   aircraft_model=self.aircraft_model)

        else:
            # Reserve all of the taxiway nodes
            taxiway_nodes = []
            for node in taxi_route:
                taxiway_node = yield self.vertiport_manager.vertiport.taxiway_node_store.get(
                    lambda filt: filt == node)
                taxiway_nodes.append(taxiway_node)

            next_node = taxi_route.pop(0)
            # Move from first node to the next node over an edge
            node_to_node_move_time = int(round(self.vertiport_manager.vertiport.vertiport_layout.
                                               node_distances.loc[
                                                   first_node, next_node] / self.ground_taxi_speed * 1000))
            yield self.env.timeout(node_to_node_move_time)

            # Save the location and time of the current node
            self.event_saver.save_location_time_info(
                node=next_node,
                agent_id=self.tail_number,
                agent_type='aircraft',
                aircraft_model=self.aircraft_model
            )

            previous_node = next_node

            if operation_type == 'arrival':
                # Release the FATO pad resource after reaching to the nextNode
                assigned_fato_resource.fato_resource.release(aircraft_fato_usage_request)

                # Decrease the aircraft arrival queue counter
                self.event_saver.update_aircraft_arrival_queue_counter(queue_update=-1)

            if operation_type == 'departure':
                # Release the parking space of the departing aircraft
                self.vertiport_manager.release_parking_space(parking_space)

            # Put back the passed edge between the first node and the next node
            # Don't need to put back the first and last node because they are
            # handled by the vertiport manager.
            self.vertiport_manager.vertiport.edge_store.put(taxiway_edges.pop(0))

            for idx, node in enumerate(taxi_route):
                # Move between taxi nodes over taxi edges
                node_to_node_move_time = int(round(self.vertiport_manager.vertiport.vertiport_layout.node_distances.
                                                   loc[previous_node, node] / self.ground_taxi_speed * 1000))
                yield self.env.timeout(node_to_node_move_time)

                # Save the location and time of the current node
                self.event_saver.save_location_time_info(
                    node=next_node,
                    agent_id=self.tail_number,
                    agent_type='aircraft',
                    aircraft_model=self.aircraft_model
                )
                if operation_type == 'departure':
                    # Save passenger location and time
                    for passenger in departing_passengers:
                        self.event_saver.save_location_time_info(
                            node=next_node,
                            agent_id=passenger.passenger_id,
                            agent_type='passenger',
                            aircraft_model=None
                        )

                # Put back the previous node and edge
                self.vertiport_manager.vertiport.taxiway_node_store.put(previous_node)
                self.vertiport_manager.vertiport.edge_store.put(taxiway_edges.pop(0))
                previous_node = node

            node_to_node_move_time = int(round(self.vertiport_manager.vertiport.vertiport_layout.node_distances.loc[
                                                   previous_node, last_node] / self.ground_taxi_speed * 1000))
            yield self.env.timeout(node_to_node_move_time)

            # Save park time
            if operation_type == 'arrival':
                self.event_saver.save_parking_info(parking_pad_id=parking_space_id,
                                                   agent_id=self.tail_number,
                                                   aircraft_model=self.aircraft_model)

            # Put back the previous node and edge
            self.vertiport_manager.vertiport.taxiway_node_store.put(previous_node)
            self.vertiport_manager.vertiport.edge_store.put(taxiway_edges.pop(0))

    def get_taxi_instructions(self, assigned_fato_id, parking_space_id):
        # Get the taxi route nodes from vertiport manager
        taxi_route, _ = self.vertiport_manager.generate_taxi_route_nodes(
            assigned_fato_id, parking_space_id)

        # Get the taxi route edges from vertiport manager
        taxi_route_edges = self.vertiport_manager.generate_taxi_route_edges(taxi_route)
        return taxi_route, taxi_route_edges

    def aircraft_take_off_process(self, time_rotor_spin_up, time_hover_climb, time_climb_transition, take_off_fato_id,
                                  time_pre_take_off_check_list, time_tug_disconnection, departing_passengers):
        self.event_saver.save_fato_arrival_info(assigned_fato_id=take_off_fato_id,
                                                agent_id=self.tail_number,
                                                agent_type='aircraft',
                                                aircraft_model=self.aircraft_model)

        # Save passenger location and time
        for passenger in departing_passengers:
            self.event_saver.save_fato_arrival_info(assigned_fato_id=take_off_fato_id,
                                                    agent_id=passenger.passenger_id,
                                                    agent_type='passenger',
                                                    aircraft_model=None
                                                    )
        yield self.env.timeout(time_tug_disconnection)
        yield self.env.timeout(time_pre_take_off_check_list)
        yield self.env.timeout(time_rotor_spin_up)
        self.event_saver.save_take_off_info(assigned_fato_id=take_off_fato_id,
                                            agent_id=self.tail_number,
                                            agent_type='aircraft',
                                            aircraft_model=self.aircraft_model)
        # Save passenger location and time
        for passenger in departing_passengers:
            self.event_saver.save_take_off_info(assigned_fato_id=take_off_fato_id,
                                                agent_id=passenger.passenger_id,
                                                agent_type='passenger',
                                                aircraft_model=None
                                                )
        yield self.env.timeout(time_hover_climb)
        yield self.env.timeout(time_climb_transition)
        self.event_saver.save_departure_fix_info(take_off_fato_id=take_off_fato_id,
                                                 agent_id=self.tail_number,
                                                 agent_type='aircraft',
                                                 aircraft_model=self.aircraft_model)
        # Save passenger location and time
        for passenger in departing_passengers:
            self.event_saver.save_departure_fix_info(take_off_fato_id=take_off_fato_id,
                                                     agent_id=passenger.passenger_id,
                                                     agent_type='passenger',
                                                     aircraft_model=None
                                                     )

    def request_charger(self):
        """
        This method is used when the charger configuration is normal (any parking pads can use any chargers).
        """
        return self.vertiport_manager.vertiport.charger_resource.request()

    def get_charging_time(self):
        charge_time = self.vertiport_manager.charging_time_distribution.pick_number_from_distribution()
        return max(0, charge_time)

    def charge_aircraft(self, charge_time: float, time_passenger_embark_disembark: float, parking_space: object,
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

        self.event_saver.save_charging_start_time(charging_location=parking_space.parking_space_id,
                                                  agent_id=self.tail_number,
                                                  event='charging_started',
                                                  aircraft_model=self.aircraft_model)
        self.charging_start_time = self.env.now

        # Actual charging happens here
        yield self.env.timeout(self.get_charging_time())

        self.event_saver.save_charging_finish_time(charging_location=parking_space.parking_space_id,
                                                   agent_id=self.tail_number,
                                                   event='charging_finished',
                                                   aircraft_model=self.aircraft_model)

        if shared_charger:
            used_charger_resource.release(selected_charging_request)
        else:
            self.vertiport_manager.vertiport.charger_resource.release(charging_request)

        self.event_saver.save_turnaround_info(charging_location=parking_space.parking_space_id,
                                              agent_id=self.tail_number,
                                              agent_type='aircraft',
                                              aircraft_model=self.aircraft_model)

        # TODO

    # def update_charge_level(self, charge_time: float) -> None:
    #     """
    #     Updates the charge level of the aircraft.
    #     """
    #     self.charge_level = min(100, self.charge_level + self.charge_rate * charge_time)

    def unload_passengers(self, passenger_disembark_time):
        yield self.env.timeout(passenger_disembark_time)
        self.event_saver.aircraft_dict[self.tail_number]['passenger_unloading_finished'] = \
            timestamp_to_datetime(self.event_saver.sim_start_timestamp, self.env.now)
    #
    # def simulate_aircraft(self):
    #     self.event_saver.save_agent_creation_time(agent_id=self.tail_number,
    #                                               agent_type='aircraft',
    #                                               aircraft_model=self.aircraft_model)
    #     # parking space and FATO reservation for landing
    #     parking_space = yield self.vertiport_manager.get_parking_pad()
    #     parking_space_id = parking_space.parking_space_id
    #
    #     # Currently, vertiport manager assigns the closest FATO
    #     assigned_fato_id = self.vertiport_manager.assign_fato(parking_space_id)
    #
    #     # Aircraft calls the FATO resource that will be requested.
    #     assigned_fato_resource = self.call_fato_resource(assigned_fato_id)
    #     # Request for FATO pad usage
    #     aircraft_fato_usage_request = self.vertiport_manager.request_fato(
    #         assigned_fato_resource=assigned_fato_resource,
    #         operation_type='arrival'
    #     )
    #     yield aircraft_fato_usage_request
    #
    #     # Landing process
    #     yield self.env.process(
    #         self.aircraft_landing_process(
    #             time_descend_transition=self.time_descend_transition,
    #             time_hover_descend=self.time_hover_descend,
    #             time_rotor_spin_down=self.time_rotor_spin_down,
    #             landing_fato_id=assigned_fato_id,
    #             time_post_landing_safety_checks=self.time_post_landing_safety_checks,
    #             time_tug_connection=self.time_tug_connection
    #         )
    #     )
    #
    #     # Get the taxi route
    #     taxi_route, taxi_route_edges = self.get_taxi_instructions(
    #         assigned_fato_id,
    #         parking_space_id
    #     )
    #
    #     # Taxi-in process
    #     yield self.env.process(
    #         self.taxi(
    #             taxi_route=taxi_route,
    #             taxi_route_edges=taxi_route_edges,
    #             assigned_fato_resource=assigned_fato_resource,
    #             parking_space_id=parking_space_id,
    #             parking_space=parking_space,
    #             aircraft_fato_usage_request=aircraft_fato_usage_request,
    #             operation_type='arrival'
    #         )
    #     )
    #
    #     # Put the aircraft into active aircraft list
    #     self.vertiport_manager.active_aircraft_store.put(self.tail_number)
    #
    #     # Charge the aircraft
    #     yield self.env.process(
    #         self.charge_aircraft(
    #             charge_time=self.time_charging,
    #             time_passenger_embark_disembark=self.time_passenger_embark_disembark,
    #             parking_space=parking_space,
    #             time_pre_charging_processes=self.time_pre_charging_processes,
    #             time_post_charging_processes=self.time_post_charging_processes,
    #             time_charging_plug_disconnection=self.time_charging_plug_disconnection,
    #             shared_charger=self.vertiport_manager.vertiport.shared_charger_sets
    #         )
    #     )
    #
    #     # Take out the aircraft from active aircraft list and put it into available aircraft list
    #     self.vertiport_manager.active_aircraft_store.get(lambda filt: filt == self.tail_number)
    #     self.vertiport_manager.available_aircraft_store.put(self.tail_number)
    #
    #     # Aircraft take off request
    #     assigned_fato_id = self.vertiport_manager.assign_fato(parking_space_id)
    #
    #     # Aircraft calls the FATO resource that will be requested.
    #     assigned_fato_resource = self.call_fato_resource(assigned_fato_id)
    #
    #     # Request for FATO pad usage
    #     aircraft_fato_usage_request = self.vertiport_manager.request_fato(
    #         assigned_fato_resource=assigned_fato_resource,
    #         operation_type='departure'
    #     )
    #     yield aircraft_fato_usage_request
    #
    #     taxi_usage_request = self.vertiport_manager.request_taxi_resource()
    #     if taxi_usage_request is not None:
    #         yield taxi_usage_request
    #
    #     # Save pushback time
    #     self.event_saver.save_pushback_info(
    #         pushback_location=parking_space_id,
    #         agent_id=self.tail_number,
    #         aircraft_model=self.aircraft_model
    #     )
    #
    #     # Taxi-out process
    #     taxi_route, taxi_route_edges = self.get_taxi_instructions(parking_space_id, assigned_fato_id)
    #     yield self.env.process(
    #         self.taxi(
    #             taxi_route=taxi_route,
    #             taxi_route_edges=taxi_route_edges,
    #             assigned_fato_resource=assigned_fato_resource,
    #             parking_space_id=parking_space_id,
    #             parking_space=parking_space,
    #             aircraft_fato_usage_request=aircraft_fato_usage_request,
    #             operation_type='departure'
    #         )
    #     )
    #
    #     # Take-off process
    #     yield self.env.process(
    #         self.aircraft_take_off_process(
    #             time_rotor_spin_up=self.time_rotor_spin_up,
    #             time_hover_climb=self.time_hover_climb,
    #             time_climb_transition=self.time_climb_transition,
    #             take_off_fato_id=assigned_fato_id,
    #             time_pre_take_off_check_list=self.time_pre_take_off_check_list,
    #             time_tug_disconnection=self.time_tug_disconnection
    #         )
    #     )
    #
    #     self.vertiport_manager.release_taxi_usage_request(taxi_usage_request)
    #     # Release the FATO
    #     assigned_fato_resource.fato_resource.release(aircraft_fato_usage_request)
