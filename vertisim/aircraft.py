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

    def __init__(self, 
                 env, 
                 tail_number, 
                 origin_vertiport_id,
                 destination_vertiport_id,
                 passengers_onboard, 
                 soc,
                 arrival_time, 
                 departure_time,
                 location,
                 serviced_time_at_the_location,
                 priority,
                 aircraft_params, 
                 vertiport_manager, 
                 event_saver):
        self.env = env
        self.tail_number = tail_number
        self._soc = soc
        self._origin_vertiport_id = origin_vertiport_id   
        self._destination_vertiport_id = destination_vertiport_id
        self._location = location
        self._serviced_time_at_the_location = serviced_time_at_the_location
        self._passengers_onboard = passengers_onboard
        self._arrival_time = arrival_time # TODO: Update this at every holding fix arrival
        self._departure_time = departure_time
        self._priority = priority        

        self.charging_start_time = None
        self.charging_end_time = None
        self.parking_space = None
        self.parking_space_id = None
        self.assigned_fato_id = None
        self.assigned_fato_resource = None
        self.holding_time = None # event_saver.aircraft_arrival_queue_waiting_time keeps track of this for every aircraft at every vertiport

        self.arrival_fix_usage_request = None
        self.departure_fix_usage_request = None
        self.aircraft_fato_usage_request = None


        self.aircraft_model = aircraft_params['aircraft_model']
        self.passenger_capacity = aircraft_params['pax']
        self.max_range = aircraft_params['range']
        self.battery_capacity = aircraft_params['battery_capacity']
        self.ground_taxi_speed = aircraft_params['ground_taxi_speed']
        self.cruise_speed = aircraft_params['cruise_speed']
        self.climb_speed = aircraft_params['climb_speed']
        self.descent_speed = aircraft_params['descent_speed']
        self.vertical_takeoff_speed = aircraft_params['vertical_takeoff_speed']
        self.vertical_landing_speed = aircraft_params['vertical_landing_speed']

        self.time_passenger_embark_disembark = sec_to_ms(aircraft_params['time_passenger_embark_disembark'])
        self.time_descend_transition = sec_to_ms(aircraft_params['time_descend_transition'])
        self.time_hover_descend = sec_to_ms(aircraft_params['time_hover_descend'])
        self.time_rotor_spin_down = sec_to_ms(aircraft_params['time_rotor_spin_down'])
        self.time_post_landing_safety_checks = sec_to_ms(aircraft_params['time_post_landing_safety_checks'])
        self.time_tug_connection = sec_to_ms(aircraft_params['time_tug_connection'])
        self.time_tug_disconnection = sec_to_ms(aircraft_params['time_tug_disconnection'])

        self.time_pre_charging_processes = sec_to_ms(aircraft_params['time_pre_charging_processes'])
        self.time_charging = sec_to_ms(aircraft_params['time_charging'])
        self.time_charging_plug_disconnection = sec_to_ms(aircraft_params['time_charging_plug_disconnection'])
        self.time_post_charging_processes = sec_to_ms(aircraft_params['time_post_charging_processes'])

        self.time_pre_take_off_check_list = sec_to_ms(aircraft_params['time_pre_take_off_check_list'])
        self.time_rotor_spin_up = sec_to_ms(aircraft_params['time_rotor_spin_up'])
        self.time_hover_climb = sec_to_ms(aircraft_params['time_hover_climb'])
        self.time_climb_transition = sec_to_ms(aircraft_params['time_climb_transition'])
        self.vertiport_manager = vertiport_manager
        self.event_saver = event_saver

    @property
    def soc(self):
        return self._soc
    
    @soc.setter
    def soc(self, value):
        if self._soc <= 0:
            self._soc = 0
        elif self._soc >= 100:
            self._soc = 100
        else:
            self._soc = value

    @property
    def origin_vertiport_id(self):
        return self._origin_vertiport_id
    
    @origin_vertiport_id.setter
    def origin_vertiport_id(self, value):
        if value in self.vertiport_manager.vertiport_ids:
            self._origin_vertiport_id = value
        else:
            raise ValueError(f"Vertiport with id {value} does not exist in the vertiport network")
        
    @property
    def destination_vertiport_id(self):
        return self._destination_vertiport_id
    
    @destination_vertiport_id.setter
    def destination_vertiport_id(self, value):
        if value in self.vertiport_manager.vertiport_ids:
            self._destination_vertiport_id = value
        else:
            raise ValueError(f"Vertiport with id {value} does not exist in the vertiport network")
        
    @property
    def serviced_time_at_the_location(self):
        return self._serviced_time_at_the_location
    
    @serviced_time_at_the_location.setter
    def serviced_time_at_the_location(self, value):
        self._serviced_time_at_the_location = value

    @property
    def passengers_onboard(self):
        return self._passengers_onboard
    
    @passengers_onboard.setter
    def passengers_onboard(self, value):
        self._passengers_onboard = value

    @property
    def arrival_time(self):
        return self._arrival_time
    
    @arrival_time.setter
    def arrival_time(self, value):
        self._arrival_time = value

    @property
    def departure_time(self):
        return self._departure_time
    
    @departure_time.setter
    def departure_time(self, value):
        self._departure_time = value
    
    @property
    def priority(self):
        return self._priority
    
    @priority.setter
    def priority(self, value):
        self._priority = value

    @property
    def location(self):
        return self._location
    
    @location.setter
    def location(self, value):
        if value in self.vertiport_manager.node_locations.keys():
            self._location = value
        else:
            raise ValueError(f"Location with id {value} does not exist in the vertiport network")    

    # @property
    # def external_location_input(self):
    #     return self._location

    # @external_location_input.setter
    # def external_location_input(self, value):
    #     if value == None:
    #         self._location = value
    #     # Detect the class of the input location from node_locations
    #     elif value in self.vertiport_manager.node_locations.keys():

         

    def __str__(self):
        return f"Aircraft {self.tail_number}:\n" \
            f"  - Origin: {self.origin_vertiport_id}\n" \
            f"  - Destination: {self.destination_vertiport_id}\n" \
            f"  - Passengers: {self.passengers_onboard}\n" \
            f"  - SOC: {self.soc}%\n" \
            f"  - Arrival Time: {self.arrival_time}\n" \
            f"  - Departure Time: {self.departure_time}\n" \
            f"  - Location: {self.location}\n" \
            f"  - Serviced Time at Location: {self.serviced_time_at_the_location}\n"


    def aircraft_landing_process(self, landing_fato_id):

        yield self.env.timeout(self.time_descend_transition)
        yield self.env.timeout(self.time_hover_descend)
        self.location = landing_fato_id
        # Save landing information
        self.event_saver.save_agent_location(agent_id=self.tail_number,
                                             agent_type='aircraft',
                                             location_id=self.location)
        yield self.env.timeout(self.time_rotor_spin_down)
        yield self.env.timeout(self.time_post_landing_safety_checks)
        yield self.env.timeout(self.time_tug_connection)
        # Save landing information
        self.event_saver.save_agent_location(agent_id=self.tail_number,
                                             agent_type='aircraft',
                                             location_id=self.location)

    def taxi(self, 
             taxi_route: list, 
             taxi_route_edges: list, 
             operation_type: str) -> None:
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
        """
        if operation_type == 'arrival':
            vertiport_id = self.destination_vertiport_id
        elif operation_type == 'departure':
            vertiport_id = self.origin_vertiport_id
        # Check whether the vertiport has a parking pad or not. If it has a parking pad then the aircraft will taxi. Otherwise, it will be parked on the FATO pad.
        if len(taxi_route) == 0:
            if operation_type == 'arrival':
                # Decrease the aircraft arrival queue counter
                self.event_saver.update_aircraft_arrival_queue_counter(vertiport_id=vertiport_id,
                                                                       queue_update=-1)     
                self.event_saver.save_agent_location(agent_id=self.tail_number,
                                                     agent_type='aircraft',
                                                     location_id=self.assigned_fato_resource.resource_id)
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
                self.assigned_fato_resource.fato_resource.release(self.aircraft_fato_usage_request)
                self.assigned_fato_resource = None
                self.assigned_fato_id = None

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
                                                             departure_parking_space=self.parking_space)
                self.parking_space = None
                self.parking_space_id = None

            node_to_node_move_time = int(round(self.vertiport_manager.vertiports[vertiport_id].vertiport_layout.
                                               node_distances.loc[
                                                   first_node, last_node] / self.ground_taxi_speed * 1000))
            yield self.env.timeout(node_to_node_move_time)

            self.location = self.parking_space_id

            # Save park time
            if operation_type == 'arrival':
                self.event_saver.save_agent_location(agent_id=self.tail_number,
                                                     agent_type='aircraft',
                                                     location_id=self.location)
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

            self.location = next_node

            # Save the location and time of the current node
            self.event_saver.save_agent_location(agent_id=self.tail_number,
                                                 agent_type='aircraft',
                                                 location_id=self.location)

            previous_node = next_node

            if operation_type == 'arrival':
                # Release the FATO pad resource after reaching to the nextNode
                self.assigned_fato_resource.fato_resource.release(self.aircraft_fato_usage_request)
                self.assigned_fato_resource = None
                self.assigned_fato_id = None

                # Save FATO usage finish time
                self.event_saver.update_fato_usage_tracker(vertiport_id=vertiport_id,
                                                           fato_usage=-1)

                # Decrease the aircraft arrival queue counter
                self.event_saver.update_aircraft_arrival_queue_counter(vertiport_id=vertiport_id,
                                                                       queue_update=-1)

            if operation_type == 'departure':
                # Release the parking space of the departing aircraft
                self.vertiport_manager.release_parking_space(vertiport_id=vertiport_id,
                                                             departure_parking_space=self.parking_space)
                self.parking_space = None
                self.parking_space_id = None

            # Put back the passed edge between the first node and the next node
            # Don't need to put back the first and last node because they are
            # handled by the vertiport manager.
            self.vertiport_manager.vertiports[vertiport_id].edge_store.put(taxiway_edges.pop(0))

            for idx, node in enumerate(taxi_route):
                # Move between taxi nodes over taxi edges
                node_to_node_move_time = int(round(self.vertiport_manager.vertiports[vertiport_id].vertiport_layout.node_distances.
                                                   loc[previous_node, node] / self.ground_taxi_speed * 1000))
                yield self.env.timeout(node_to_node_move_time)

                self.location = node

                # Save the location and time of the current node
                self.event_saver.save_agent_location(agent_id=self.tail_number,
                                                     agent_type='aircraft',
                                                     location_id=self.location)

                # Put back the previous node and edge
                self.vertiport_manager.vertiports[vertiport_id].taxiway_node_store.put(previous_node)
                self.vertiport_manager.vertiports[vertiport_id].edge_store.put(taxiway_edges.pop(0))
                previous_node = node

            node_to_node_move_time = int(round(self.vertiport_manager.vertiports[vertiport_id].vertiport_layout.node_distances.loc[
                                                   previous_node, last_node] / self.ground_taxi_speed * 1000))
            yield self.env.timeout(node_to_node_move_time)
            
            self.location = last_node

            # Save park time
            if operation_type == 'arrival':
                self.event_saver.save_agent_location(agent_id=self.tail_number,
                                                     agent_type='aircraft',
                                                     location_id=self.location)

            # Put back the previous node and edge
            self.vertiport_manager.vertiports[vertiport_id].taxiway_node_store.put(previous_node)
            self.vertiport_manager.vertiports[vertiport_id].edge_store.put(taxiway_edges.pop(0))

    def aircraft_take_off_process(self, take_off_fato_id):
        self.location = take_off_fato_id
        self.event_saver.save_agent_location(agent_id=self.tail_number,
                                             agent_type='aircraft',
                                             location_id=self.location)

        yield self.env.timeout(self.time_tug_disconnection)
        yield self.env.timeout(self.time_pre_take_off_check_list)
        yield self.env.timeout(self.time_rotor_spin_up)
        self.event_saver.save_agent_location(agent_id=self.tail_number,
                                             agent_type='aircraft',
                                             location_id=self.location)
        # Save passenger location and time
        for passenger in self.passengers_onboard:
            self.event_saver.save_agent_location(agent_id=passenger.passenger_id,
                                                agent_type='passenger',
                                                location_id=self.location)
            
        yield self.env.timeout(self.time_hover_climb)
        yield self.env.timeout(self.time_climb_transition)

        # Save location and time
        self.location = self.vertiport_manager.vertiports[self.origin_vertiport_id].vertiport_layout.departure_fix_node
        self.event_saver.save_agent_location(agent_id=self.tail_number,
                                             agent_type='aircraft',
                                             location_id=self.location)
        
        # # Save passenger location and time
        for passenger in self.passengers_onboard:
            self.event_saver.save_agent_location(agent_id=passenger.passenger_id,
                                                agent_type='passenger',
                                                location_id=self.location)      
    
    def fly_in_the_airspace(self, flight_direction):
        """
        Finds the location of the aircraft in the airspace from self.vertiport_manager.airspace.airlink_resources
        and traverses the airspace starting from that location        
        """      
        # Release the departure fix
        self.vertiport_manager.release_fix_resource(aircraft=self,
                                                    fix_resource_request=self.departure_fix_usage_request,
                                                    operation_type='departure')
        self.departure_fix_usage_request = None

        link_traversal_time = hr_to_ms(self.vertiport_manager.airspace.airlink_segment_length_miles / self.cruise_speed)
        # Get the airlink resources for the flight direction
        airlink_resources = self.vertiport_manager.airspace.airlink_resources[flight_direction]

        # Check if the aircraft on the approach or departure fix. These are the edge of the airspace.
        

        # Find the current location of the aircraft in the airlink resources
        current_location_index = None
        for index, (waypoint_id, _) in enumerate(airlink_resources.items()):
            if waypoint_id == self.location:
                current_location_index = index
                break

        if current_location_index is None:
            raise ValueError(f"Aircraft's current location ({self.location}) not found in the airlink resources")

        # Start iterating the airlink resources from the current location
        for waypoint_id, resource in list(airlink_resources.items())[current_location_index:]:
            with resource.request() as req:
                yield req
                yield self.env.timeout(link_traversal_time)

            # Save location and time information
            self.event_saver.save_agent_location(agent_id=self.tail_number,
                                                agent_type='aircraft',
                                                location_id=waypoint_id)
            self.location = waypoint_id

        yield self.env.process(self.vertiport_manager.simulate_terminal_airspace_arrival_process(
            aircraft=self, arriving_passengers=self.passengers_onboard)
        )

    def request_charger(self):
        """
        This method is used when the charger configuration is normal (any parking pads can use any chargers).
        """
        return self.vertiport_manager.vertiports[self.destination_vertiport_id].charger_resource.request()

    def get_charging_time(self):
        """
        Get charging time - Two options: Constant charging time or draw a number from distribution
        """
        if self.time_charging is not None:
            return max(self.time_passenger_embark_disembark, self.time_charging)
        charge_time = sec_to_ms(self.vertiport_manager.charging_time_distribution.pick_number_from_distribution())
        charge_time = max(self.time_passenger_embark_disembark, charge_time)
        self.event_saver.save_aircraft_charging_time(vertiport_id=self.destination_vertiport_id,
                                                     aircraft_id=self.tail_number, 
                                                     charging_time=charge_time)
        return charge_time

    def charge_aircraft(self, parking_space: object, shared_charger: bool = False) -> None:
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

        self.event_saver.save_agent_location(location_id=self.parking_space.resource_id,
                                             agent_id=self.tail_number,
                                             agent_type='aircraft',
                                             event='charging_start')
        
        self.charging_start_time = self.env.now

        # Actual charging happens here
        yield self.env.timeout(self.get_charging_time())
        self.charging_end_time = self.env.now

        # Update the SOC
        self.update_charge_level(operation='charge')

        self.event_saver.save_agent_location(location_id=self.parking_space.resource_id,
                                             agent_id=self.tail_number,
                                             agent_type='aircraft',
                                             event='charging_end')

        if shared_charger:
            used_charger_resource.release(selected_charging_request)
        else:
            self.vertiport_manager.vertiports[self.destination_vertiport_id].charger_resource.release(charging_request)

    @staticmethod
    def calc_soc_from_charge_time(charge_time: int, initial_soc: int, df: pd.DataFrame) -> int:
        """
        charge_time is the time between the current time and the charging start time.

        Parameters
        ----------
        charge_time: int
            Time between the current time and the charging start time in miliseconds.
        soc: int
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
        idx_final_soc = df['time_sec'].sub(final_soc_time).abs().idxmin()
        return df.loc[idx_final_soc]['soc']


    def update_charge_level(self, new_soc: int = None, operation: str = 'charge') -> None:
        """
        Updates the charge level of the aircraft using current charge time.
        """
        if operation == 'charge':
            charge_time = self.env.now - self.charging_start_time
            charge_lookup_table = self.vertiport_manager.aircraft_battery_models[self.destination_vertiport_id]
            final_soc = Aircraft.calc_soc_from_charge_time(charge_time=charge_time, initial_soc=self._soc, df=charge_lookup_table)
            self._soc = min(100, final_soc)
        elif operation == 'discharge':
            self._soc = new_soc

    def check_charge_level(self):
        return self.current_soc

    def unload_passengers(self, passenger_disembark_time):
        # TODO: check
        yield self.env.timeout(passenger_disembark_time)
        self.event_saver.aircraft_dict[self.tail_number]['passenger_unloading_finished'] = \
            timestamp_to_datetime(self.event_saver.sim_start_timestamp, self.env.now)
