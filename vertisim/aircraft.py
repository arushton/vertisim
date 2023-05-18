from utils.helpers import timestamp_to_datetime, get_key_from_value
from utils.units import sec_to_ms, min_to_sec, ms_to_sec, sec_to_hr, hr_to_ms, ft_to_m, m_to_ft, mph_metersec, metersec_mph, watt_to_kw, miles_to_m
from typing import Union, Dict, List, Optional
import pandas as pd # For type hinting
import numpy as np
import random
from utils.flight_helpers import weight, lift_induced_drag_coef, rho, rotor_disk_area, \
    min_power_speed_for_climb_descend, lift_induced_drag_coef, max_range_speed, stall_speed
from utils.compute_location_from_distance_and_bearing import compute_location_from_distance_and_bearing


class Aircraft:
    """
    Aircraft agent
    """

    def __init__(self, 
                 env, 
                 tail_number, 
                 input_cruise_speed,     
                 altitude,            
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
        self.input_cruise_speed = input_cruise_speed
        self._altitude = altitude
        self._soc = soc
        self._speed = 0
        self._origin_vertiport_id = origin_vertiport_id   
        self._destination_vertiport_id = destination_vertiport_id
        self._location = location
        self._serviced_time_at_the_location = serviced_time_at_the_location
        self._passengers_onboard = passengers_onboard
        self._arrival_time = arrival_time # TODO: Update this at every holding fix arrival
        self._departure_time = departure_time
        self._priority = priority    

        self.aircraft_params = aircraft_params    

        self.flight_phase = None # ['ground', 'cruise', 'landing', 'takeoff', 'holding']
        self.charging_start_time = None
        self.charging_end_time = None
        self.parking_space = None
        self.parking_space_id = None
        self.assigned_fato_id = None
        self.assigned_fato_resource = None
        self.holding_time = None
        self.flight_direction = None

        self.arrival_fix_usage_request = None
        self.departure_fix_usage_request = None
        self.aircraft_fato_usage_request = None
        self.parking_space_usage_request = None


        self.aircraft_model = self.aircraft_params['aircraft_model']
        self.passenger_capacity = self.aircraft_params['pax']
        self.max_range = self.aircraft_params['range']
        self.battery_capacity = self.aircraft_params['battery_capacity']

        self.ground_taxi_speed = self.aircraft_params['ground_taxi_speed']
        self.vertical_takeoff_speed = self.aircraft_params['vertical_takeoff_speed']
        self.vertical_landing_speed = self.aircraft_params['vertical_landing_speed']

        self.hover_altitude = ft_to_m(aircraft_params['hover_altitude'])
        self.cruise_altitude = ft_to_m(aircraft_params['cruise_altitude'])
        self.ground_altitude = ft_to_m(self.aircraft_params['ground_altitude'])    
        self.climb_transition_end_altitude = self.hover_altitude + self.aircraft_params['time_climb_transition'] * self.vertical_takeoff_speed
           

        self.mtom = self.aircraft_params['mtom'] # Max takeoff mass
        self.wing_area = self.aircraft_params['wing_area'] # Wing area (m^2)
        self.disk_load = self.aircraft_params['disk_load'] # Disk loading (kg/m^2)    
        self.f = self.aircraft_params['f'] # Correction factor for interference from the fuselage            
        self.FoM = self.aircraft_params['FoM'] # Figure of merit
        self.cd_0 = self.aircraft_params['cd_0'] # Zero lift drag coefficient
        self.cl_max = self.aircraft_params['cl_max'] # Max lift coefficient
        self.ld_max = self.aircraft_params['ld_max'] # Max lift to drag ratio
        self.n_hover = self.aircraft_params['n_hover'] # Hover efficiency
        self.n_descend = self.aircraft_params['n_descend'] # Descend efficiency
        self.n_climb = self.aircraft_params['n_climb'] # Climb efficiency
        self.n_cruise = self.aircraft_params['n_cruise'] # Cruise efficiency
        self.atmosphere_condition = self.aircraft_params['atmosphere_condition']   

        self.stall_speed = stall_speed(atmosphere_condition=self.atmosphere_condition,
                                       altitude=self.cruise_altitude,
                                       mtom=self.mtom, 
                                       wing_area=self.wing_area, 
                                       cl_max=self.cl_max)

        self.time_passenger_embark_disembark = sec_to_ms(aircraft_params['time_passenger_embark_disembark'])
        self.time_descend = sec_to_ms(aircraft_params['time_descend'])
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
        self.time_climb = sec_to_ms(aircraft_params['time_climb'])
        self.vertiport_manager = vertiport_manager
        self.event_saver = event_saver
        self.soc_required_to_complete_mission = 30 # TODO: Complete calc_soc_required_for_flight function

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

    def update_soc(self, value):
        self._soc += value

    @property
    def speed(self):
        return self._speed
    
    @speed.setter
    def speed(self, value):
        # if self._speed <= 0:
        #     self._speed = 0
        # else:
        self._speed = value

    @property
    def altitude(self):
        return self._altitude
    
    @altitude.setter
    def altitude(self, value):
        if self._altitude <= 0:
            self._altitude = 0
        else:
            self._altitude = value

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


    def aircraft_landing_process(self):
        min_power_speed = min_power_speed_for_climb_descend(atmosphere_condition=self.atmosphere_condition,
                                                            altitude=self.cruise_altitude,
                                                            mtom=self.compute_flight_mass(),
                                                            cd_0=self.cd_0,
                                                            wing_area=self.wing_area,
                                                            ld_max=self.ld_max)
        self.speed = min_power_speed
        # Descend
        self.flight_phase = 'landing'
        yield self.env.timeout(self.time_descend)
        descend_energy_consumption = self.descend_energy_consumption(min_power_speed=self.speed)
        self.soc_discharge_update(descend_energy_consumption)
        # self.update_altitude(vertical_speed=-self.vertical_landing_speed, time=ms_to_sec(self.time_descend)) # TODO: Are you going to use this approach or get the altitude as an input?
        self.location = self.vertiport_manager.get_last_airlink_node_id(self.flight_direction)
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='descend')

        # Request FATO - Aircraft already have a parking pad
        yield self.env.process(self.vertiport_manager.fato_pad_request(aircraft=self, operation_type='arrival'))

        # Descend transition
        yield self.env.timeout(self.time_descend_transition)
        descend_transition_energy_consumption = self.descend_transition_energy_consumption(min_power_speed=self.speed)
        self.soc_discharge_update(descend_transition_energy_consumption)
        # self.update_altitude(vertical_speed=-self.vertical_landing_speed, time=ms_to_sec(self.time_descend_transition))
        self.location = self.assigned_fato_id
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='descend_transition', altitude=self.hover_altitude+self.vertiport_manager.vertiports[self.destination_vertiport_id].vertiport_layout.vertiport_height)

        # Hover descend
        yield self.env.timeout(self.time_hover_descend)
        hover_descend_energy_consumption = self.vertical_takeoff_landing_energy_consumption(operation='landing')
        self.soc_discharge_update(hover_descend_energy_consumption)
        self.speed = 0
        self.flight_phase = 'ground'
        # Save landing information
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='hover_descend')

        yield self.env.timeout(self.time_rotor_spin_down)
        yield self.env.timeout(self.time_post_landing_safety_checks)
        yield self.env.timeout(self.time_tug_connection)
        # Save landing information
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='landed')

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
                self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='parked_on_fato_pad')
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

            self.speed = self.ground_taxi_speed
            node_to_node_move_time = int(round(self.vertiport_manager.vertiports[vertiport_id].vertiport_layout.
                                               node_distances.loc[
                                                   first_node, last_node] / self.ground_taxi_speed * 1000))
            yield self.env.timeout(node_to_node_move_time)

            self.speed = 0
            self.location = self.parking_space_id

            # Save park time
            if operation_type == 'arrival':
                self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='parked')
        else:
            # Reserve all of the taxiway nodes
            taxiway_nodes = []
            for node in taxi_route:
                taxiway_node = yield self.vertiport_manager.vertiports[vertiport_id].taxiway_node_store.get(
                    lambda filt: filt == node)
                taxiway_nodes.append(taxiway_node)

            next_node = taxi_route.pop(0)

            self.speed = self.ground_taxi_speed            
            # Move from first node to the next node over an edge
            node_to_node_move_time = int(round(self.vertiport_manager.vertiports[vertiport_id].vertiport_layout.
                                               node_distances.loc[
                                                   first_node, next_node] / self.ground_taxi_speed * 1000))
            yield self.env.timeout(node_to_node_move_time)

            self.location = next_node

            # Save the location and time of the current node
            self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='taxiing')

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
                self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='taxiing')

                # Put back the previous node and edge
                self.vertiport_manager.vertiports[vertiport_id].taxiway_node_store.put(previous_node)
                self.vertiport_manager.vertiports[vertiport_id].edge_store.put(taxiway_edges.pop(0))
                previous_node = node

            node_to_node_move_time = int(round(self.vertiport_manager.vertiports[vertiport_id].vertiport_layout.node_distances.loc[
                                                   previous_node, last_node] / self.ground_taxi_speed * 1000))
            yield self.env.timeout(node_to_node_move_time)
            
            self.location = last_node
            self.speed = 0            

            # Save park time
            if operation_type == 'arrival':
                self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='parked')

            # Put back the previous node and edge
            self.vertiport_manager.vertiports[vertiport_id].taxiway_node_store.put(previous_node)
            self.vertiport_manager.vertiports[vertiport_id].edge_store.put(taxiway_edges.pop(0))

    def aircraft_take_off_process(self, take_off_fato_id):
        self.departure_time = self.env.now
        self.location = take_off_fato_id
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='fato_arrival')

        # Save passenger departure time
        for passenger in self.passengers_onboard:
            passenger.departure_time = self.env.now    
            self.event_saver.save_agent_state(agent=passenger, agent_type='passenger', event='fato_arrival')    

        yield self.env.timeout(self.time_tug_disconnection)
        yield self.env.timeout(self.time_pre_take_off_check_list)
        yield self.env.timeout(self.time_rotor_spin_up)
        
        # Hover climb
        self.speed = 0 # horizontal speed
        yield self.env.timeout(self.time_hover_climb)
        hover_climb_energy_consumption = self.vertical_takeoff_landing_energy_consumption(operation='takeoff')
        self.soc_discharge_update(hover_climb_energy_consumption)
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='hover_climb', altitude=self.hover_altitude+self.vertiport_manager.vertiports[self.origin_vertiport_id].vertiport_layout.vertiport_height)

        # Climb transition
        yield self.env.timeout(self.time_climb_transition)
        min_power_speed = min_power_speed_for_climb_descend(atmosphere_condition=self.atmosphere_condition,
                                                            altitude=self.hover_altitude,
                                                            mtom=self.compute_flight_mass(),
                                                            cd_0=self.cd_0,
                                                            wing_area=self.wing_area,
                                                            ld_max=self.ld_max)
        self.speed = min_power_speed
        climb_transition_energy_consumption = self.climb_transition_energy_consumption(min_power_speed=min_power_speed)
        self.soc_discharge_update(climb_transition_energy_consumption)
        self.location = self.vertiport_manager.get_first_airlink_node_id(flight_direction=self.flight_direction) # First airlink resource is the departure fix
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='climb_transition')

        # Release the departure fix
        departure_fix = self.vertiport_manager.get_first_airlink_resource(flight_direction=self.flight_direction)
        departure_fix.release(self.departure_fix_usage_request)
        self.departure_fix_usage_request = None

        # Climb to cruise altitude
        first_waypoint = self.vertiport_manager.get_second_airlink_node_id(flight_direction=self.flight_direction) # Second airlink resource is the first waypoint
        first_waypoint_resource = self.vertiport_manager.get_second_airlink_resource(flight_direction=self.flight_direction) # First airlink resource is the departure fix
        with first_waypoint_resource.request() as req:
            yield req
            yield self.env.timeout(self.time_climb)
        climb_energy_consumption = self.climb_energy_consumption(min_power_speed=min_power_speed)
        self.soc_discharge_update(climb_energy_consumption)
        self.location = first_waypoint
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='climb')
        self.altitude = self.cruise_altitude
    
    def fly_in_the_airspace(self, user_modification=False):
        """
        Finds the location of the aircraft in the airspace from self.vertiport_manager.airspace.airlink_resources
        and traverses the airspace starting from that location        
        """      
        self.speed = max_range_speed(atmosphere_condition=self.atmosphere_condition,
                                     altitude=self.cruise_altitude,
                                     mtom=self.compute_flight_mass(),
                                     cd_0=self.cd_0,
                                     wing_area=self.wing_area,
                                     ld_max=self.ld_max)

        # Get the airlink resources for the flight direction
        airlink_resources = self.vertiport_manager.airspace.airlink_resources[self.flight_direction]

        # Find the current location of the aircraft in the airlink resources
        current_location_index = None
        for index, (waypoint_id, _) in enumerate(airlink_resources.items()):
            if waypoint_id == self.location:
                current_location_index = index
                break

        if current_location_index is None:
            raise ValueError(f"Aircraft's current location ({self.location}) not found in the airlink resources")

        # Start iterating the airlink resources from the next location. Last node is the final approach fix. We don't request it here.
        if user_modification:
            starting_index = current_location_index
        else:
            starting_index = current_location_index + 1
        for waypoint_id, resource in list(airlink_resources.items())[starting_index:-1]:
            with resource.request() as req:
                yield req
                link_traversal_time = sec_to_ms(round(miles_to_m(self.vertiport_manager.airspace.airlink_segment_length_miles) / self.speed))
                yield self.env.timeout(link_traversal_time)
            # Compute energy consumption
            cruise_energy_consumption = self.cruise_energy_consumption(velocity=self.speed, time_cruise=ms_to_sec(link_traversal_time))
            self.soc_discharge_update(cruise_energy_consumption)
            # Save location and time information
            self.location = waypoint_id
            self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='cruise')          

        yield self.env.process(self.vertiport_manager.simulate_terminal_airspace_arrival_process(
            aircraft=self, arriving_passengers=self.passengers_onboard)
        )

        # TODO: distance_to_descend_start_from_approach_fix = self.aircraft_params['time_descend'] * self.v_max_power
        # num_waypoints_before_approach_fix = int(distance_to_descend_start_from_approach_fix/ miles_to_m(airlink_segment_length_miles))
        # First request parking pad. If no available parking pad, then hold with cruise speed. Once you get the parking pad, descend and Once the descend finishes, request the fato.

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
        if self.soc >= self.soc_required_to_complete_mission:
            self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='no_charge_needed') 
            self.charging_start_time = self.env.now
            self.charging_end_time = self.env.now
            return
        
        # time_before_charger_allocation = self.env.now

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

        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='charging_start')        
        
        self.charging_start_time = self.env.now

        # Actual charging happens here
        yield self.env.timeout(self.get_charging_time())
        self.charging_end_time = self.env.now

        # Update the SOC
        self.soc_charge_update()

        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='charging_end')

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
        # Get the time at initial soc level
        initial_soc_time = df[df.soc == initial_soc]['time_sec'].values[0]
        # Get the time at final soc level
        final_soc_time = initial_soc_time + ms_to_sec(charge_time)
        # Get the soc at final soc level
        idx_final_soc = df['time_sec'].sub(final_soc_time).abs().idxmin()
        return df.loc[idx_final_soc]['soc']


    def soc_charge_update(self) -> None:
        """
        Updates the charge level of the aircraft using current charge time.
        """
        charge_time = self.env.now - self.charging_start_time
        charge_lookup_table = self.vertiport_manager.aircraft_battery_models[self.destination_vertiport_id]
        final_soc = Aircraft.calc_soc_from_charge_time(charge_time=charge_time, initial_soc=self.soc, df=charge_lookup_table)
        self._soc = min(100, final_soc)

    def convert_kwh_soc(self, kwh: float) -> int:
        """
        Converts kwh to aircraft's soc level.
        """
        return kwh / self.battery_capacity * 100
    
    def soc_discharge_update(self, kwh: float) -> None:
        """
        Updates the charge level of the aircraft using current charge time.
        """
        self.update_soc(-np.floor(self.convert_kwh_soc(kwh))) # TODO: Create a soc vs time table with 0.5 increment
        self.check_reserve_energy()

    def unload_passengers(self, passenger_disembark_time):
        # TODO: check
        yield self.env.timeout(passenger_disembark_time)
        self.event_saver.aircraft_dict[self.tail_number]['passenger_unloading_finished'] = \
            timestamp_to_datetime(self.event_saver.sim_start_timestamp, self.env.now)

    def vertical_takeoff_landing_energy_consumption(self, operation: str) -> float:
        start_density = rho(altitude=self.ground_altitude, atmosphere_condition=self.atmosphere_condition) # This doesn't matter whether the operation is takeoff or landing as we take the average of the two.
        end_density = rho(altitude=self.hover_altitude, atmosphere_condition=self.atmosphere_condition)
        self.tom = self.compute_flight_mass() # Takeoff mass

        term1 = self.f * weight(self.tom) / self.FoM
        term2_start = np.sqrt(self.f * weight(self.tom) / rotor_disk_area(self.tom, self.disk_load) / (2 * start_density))
        term2_end = np.sqrt(self.f * weight(self.tom) / rotor_disk_area(self.tom, self.disk_load) / (2 * end_density))
        term3 = weight(self.tom) * mph_metersec(self.vertical_takeoff_speed) / 2

        start_power = max(watt_to_kw((term1 * term2_start + term3) / self.n_hover), 0)
        end_power = max(watt_to_kw((term1 * term2_end + term3) / self.n_hover), 0)

        print(f'vertical_start_power: {start_power}, end_power: {end_power} for vertical {operation}')

        if operation == 'takeoff':
            return sec_to_hr((start_power + end_power) / 2 * self.aircraft_params['time_hover_climb']) # kWh - time units need to be seconds
        elif operation == 'landing':
            return sec_to_hr((start_power + end_power) / 2 * self.aircraft_params['time_hover_descend'])
        else:
            raise ValueError('operation must be either takeoff or landing')


    def climb_transition_energy_consumption(self, min_power_speed) -> float:
        climb_transition_end_velocity = min_power_speed
        term1_start = self.f * weight(self.tom) / self.FoM
        term2_start = np.sqrt(self.f * weight(self.tom) / rotor_disk_area(self.tom, self.disk_load) / (2 * rho(self.hover_altitude, self.atmosphere_condition)))
        climb_transition_start_power = max(watt_to_kw((term1_start * term2_start)/ self.n_hover), 0)

        term1_end = weight(self.tom) * mph_metersec(self.vertical_takeoff_speed)
        term2_end = 1/2 * rho(self.climb_transition_end_altitude, self.atmosphere_condition) \
            * self.wing_area * self.cd_0 * climb_transition_end_velocity ** 3
        term3_end = lift_induced_drag_coef(cd_0=self.cd_0, ld_max=self.ld_max) \
            * weight(self.tom)**2 / (1/2*rho(self.climb_transition_end_altitude, self.atmosphere_condition) \
                                       * self.wing_area * climb_transition_end_velocity)
        climb_transition_end_power = max(watt_to_kw((term1_end + term2_end + term3_end) / self.n_climb), 0)

        print(f'climb_transition_start_power: {climb_transition_start_power}, climb_transition_end_power: {climb_transition_end_power}')

        return sec_to_hr((climb_transition_start_power + climb_transition_end_power) / 2 * self.aircraft_params['time_climb_transition'])
    
    def descend_transition_energy_consumption(self, min_power_speed) -> float:
        descend_transition_start_velocity = min_power_speed
        term1_start = weight(self.tom) * mph_metersec(self.vertical_landing_speed)
        term2_start = 1/2 * rho(self.climb_transition_end_altitude, self.atmosphere_condition) \
            * self.wing_area * self.cd_0 * descend_transition_start_velocity ** 3
        term3_start = lift_induced_drag_coef(cd_0=self.cd_0, ld_max=self.ld_max) \
            * weight(self.tom)**2 / (1/2*rho(self.climb_transition_end_altitude, self.atmosphere_condition) * descend_transition_start_velocity)
        descend_transition_start_power = max(watt_to_kw(-term1_start + term2_start / self.n_climb + term3_start / self.n_climb), 0)

        term1_end = self.f * weight(self.tom) / self.FoM
        term2_end = np.sqrt(self.f * weight(self.tom) / rotor_disk_area(self.tom, self.disk_load) / (2 * rho(self.hover_altitude, self.atmosphere_condition)))
        descend_transition_end_power = max(watt_to_kw((term1_end * term2_end)/ self.n_hover), 0) 

        print(f'descend_transition_start_power: {descend_transition_start_power}, descend_transition_end_power: {descend_transition_end_power}')

        return sec_to_hr((descend_transition_start_power + descend_transition_end_power) / 2 * self.aircraft_params['time_descend_transition'])

    def climb_energy_consumption(self, min_power_speed) -> float:
        K = lift_induced_drag_coef(cd_0=self.cd_0, ld_max=self.ld_max) * 4/3 # New K to account for L/D correction

        term1_start = weight(self.tom) * mph_metersec(self.vertical_takeoff_speed)
        term2_start = 1/2 * rho(self.climb_transition_end_altitude, self.atmosphere_condition) \
            * self.wing_area * self.cd_0 * min_power_speed ** 3
        term3_start = K * weight(self.tom)**2 / (1/2*rho(self.climb_transition_end_altitude, self.atmosphere_condition) \
                                       * self.wing_area * min_power_speed)
        climb_start_power = max(watt_to_kw((term1_start + term2_start + term3_start) / self.n_climb), 0)

        term1_end = weight(self.tom) * mph_metersec(self.vertical_takeoff_speed)
        term2_end = 1/2 * rho(self.cruise_altitude, self.atmosphere_condition) \
            * self.wing_area * self.cd_0 * min_power_speed ** 3
        term3_end = K * weight(self.tom)**2 / (1/2*rho(self.cruise_altitude, self.atmosphere_condition) * self.wing_area * min_power_speed)
        climb_end_power = max(watt_to_kw(-term1_end + term2_end / self.n_climb + term3_end / self.n_climb), 0)

        print(f'climb_start_power: {climb_start_power}, climb_end_power: {climb_end_power}')

        return sec_to_hr((climb_start_power + climb_end_power) / 2 * self.aircraft_params['time_climb'])
    
    def descend_energy_consumption(self, min_power_speed) -> float:
        K = lift_induced_drag_coef(cd_0=self.cd_0, ld_max=self.ld_max) * 4/3

        term1_start = weight(self.tom) * mph_metersec(self.vertical_landing_speed)
        term2_start = 1/2 * rho(self.cruise_altitude, self.atmosphere_condition) \
            * self.wing_area * self.cd_0 * min_power_speed ** 3
        term3_start = K * weight(self.tom)**2 / (1/2*rho(self.cruise_altitude, self.atmosphere_condition) * self.wing_area * min_power_speed)
        descend_start_power = max(watt_to_kw(-term1_start + term2_start / self.n_climb + term3_start / self.n_climb), 0)

        term1_end = weight(self.tom) * mph_metersec(self.vertical_landing_speed)
        term2_end = 1/2 * rho(self.hover_altitude, self.atmosphere_condition) \
            * self.wing_area * self.cd_0 * min_power_speed ** 3
        term3_end = K * weight(self.tom)**2 / (1/2*rho(self.climb_transition_end_altitude, self.atmosphere_condition) * self.wing_area * min_power_speed)
        descend_end_power = max(watt_to_kw((term1_end + term2_end + term3_end) / self.n_climb), 0)

        print(f'descend_start_power: {descend_start_power}, descend_end_power: {descend_end_power}')

        return sec_to_hr((descend_start_power + descend_end_power) / 2 * self.aircraft_params['time_descend'])
    
    def cruise_energy_consumption(self, velocity, time_cruise) -> float:
        cruise_velocity = min(self.input_cruise_speed, velocity)
        cruise_velocity = max(cruise_velocity, self.stall_speed)
        cruise_power = max(watt_to_kw((weight(self.tom) * cruise_velocity) / (0.85*self.ld_max) / self.n_cruise), 0)
        return sec_to_hr(cruise_power * time_cruise)
    
    def check_reserve_energy(self) -> float:
        if self.soc <= 2 and self.flight_phase in ['landing', 'cruise', 'takeoff']:
            print(f"Aircraft {self.tail_number} is out of energy at time {self.env.now} while in {self.flight_phase} phase. The flight direction is {self.flight_direction} and it's location is {self.location}.")
        if self.soc <= 20 and self.flight_phase in ['landing', 'cruise', 'takeoff']:
            self.priority = 0

    def update_altitude(self, vertical_speed, time):
        self.altitude += vertical_speed * time
        self.altitude = max(self.altitude, 0)

    def compute_flight_mass(self, num_passenger= None) -> float:
        if num_passenger:
            return self.mtom - (self.aircraft_params['pax']-num_passenger)*self.aircraft_params['pax_mass']
        return self.mtom - (self.aircraft_params['pax']-len(self.passengers_onboard))*self.aircraft_params['pax_mass']




    
