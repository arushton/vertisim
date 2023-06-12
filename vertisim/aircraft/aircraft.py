from utils.helpers import timestamp_to_datetime, get_key_from_value, check_magnitude_order, roundup_to_five_minutes
from utils.distance import haversine_dist
from utils.units import sec_to_ms, min_to_sec, ms_to_sec, sec_to_hr, ms_to_min, hr_to_ms, ms_to_hr, ft_to_m, m_to_ft, mph_to_metersec, metersec_to_mph, watt_to_kw, miles_to_m
from typing import Union, Dict, List, Optional
import pandas as pd # For type hinting
import numpy as np
from collections import defaultdict
from aircraft.optimize_velocity import VelocityOptimizer
from utils.distance import distance_3d
from aircraft.flight_helpers import stall_speed, climb_power_consumption_for_lift, climb_power_consumption_for_drag
from utils.compute_location_from_distance_and_bearing import compute_location_from_distance_and_bearing
from aircraft.power_model import vertical_takeoff_landing_phase_power, climb_transition_phase_power, climb_phase_power, descend_phase_power, \
    cruise_phase_power, descend_transition_phase_power

class Aircraft:
    """
    Aircraft agent
    """

    def __init__(self, 
                 env, 
                 tail_number, 
                 input_cruise_speed,     
                 origin_vertiport_id,
                 destination_vertiport_id,
                 passengers_onboard, 
                 soc,
                 target_soc,
                 arrival_time, 
                 departure_time,
                 location,
                 serviced_time_at_the_location,
                 priority,
                 initial_process,
                 aircraft_params, 
                 vertiport_manager, 
                 event_saver,
                 logger,
                 aircraft_logger):
        self.env = env        
        self.tail_number = tail_number
        self.vertiport_manager = vertiport_manager
        self.event_saver = event_saver        
        self.input_cruise_speed = input_cruise_speed
        self.altitude = self.get_node_altitude(location)
        self._soc = soc
        self._speed = 0
        self._vertical_velocity = 0
        self._origin_vertiport_id = origin_vertiport_id   
        self._destination_vertiport_id = destination_vertiport_id
        self._location = location
        self._serviced_time_at_the_location = serviced_time_at_the_location
        self._passengers_onboard = passengers_onboard
        self._arrival_time = arrival_time
        self._departure_time = departure_time
        self._priority = priority
        self.initial_process = initial_process
        self.preflight_soc = self._soc

        self.aircraft_params = aircraft_params
        self.max_vertical_velocity = self.aircraft_params['max_vertical_velocity'] 
        self.max_horizontal_velocity = self.aircraft_params['max_horizontal_velocity']   

        self.state = self.initial_process # ['ground', 'cruise', 'descend', 'descend_transition', 'hover_descend', 'hover_climb', 'climb_transition', 'climb', 'holding', 'charging', 'parking', 'pushback', 'takeoff', 'landing']
        self.charging_start_time = None
        self.charging_end_time = None
        self.parking_space = None
        self.parking_space_id = None
        self.assigned_fato_id = None
        self.assigned_fato_resource = None
        self.holding_time = None
        self.idle_time = 0
        self.ground_holding_end_time = 0
        self.flight_direction = None
        self.flight_duration = None
        self.turnaround_time = None
        self.pushback_time = None
        self.total_energy_consumption = 0
        self.target_soc = target_soc

        self.arrival_fix_usage_request = None
        self.arrival_fix_resource = None
        self.departure_fix_usage_request = None
        self.departure_fix_resource = None
        self.aircraft_fato_usage_request = None
        self.parking_space_usage_request = None

        self.aircraft_model = self.aircraft_params['aircraft_model']
        self.passenger_capacity = self.aircraft_params['pax']
        self.max_range = self.aircraft_params['range']
        self.battery_capacity = self.aircraft_params['battery_capacity']

        self.ground_taxi_speed = self.aircraft_params['ground_taxi_speed']

        # -------- Not used ------------
        self.hover_altitude = aircraft_params['hover_altitude']
        self.cruise_altitude = aircraft_params['cruise_altitude']
        self.ground_altitude = self.aircraft_params['ground_altitude'] 
        # ------------------------------

        self.mtom = self.aircraft_params['mtom'] # Max takeoff mass
        self.wing_area = self.aircraft_params['wing_area'] # Wing area (m^2)
        self.disk_load = self.aircraft_params['disk_load'] # Disk loading (kg/m^2)    
        self.f = self.aircraft_params['f'] # Correction factor for interference from the fuselage            
        self.FoM = self.aircraft_params['FoM'] # Figure of merit
        self.cd_0 = self.aircraft_params['cd_0'] # Zero lift drag coefficient
        self.cl_max = self.aircraft_params['cl_max'] # Max lift coefficient
        self.ld_max = self.aircraft_params['ld_max'] # Max lift to drag ratio
        self.eta_hover = self.aircraft_params['eta_hover'] # Hover efficiency
        self.eta_descend = self.aircraft_params['eta_descend'] # Descend efficiency
        self.eta_climb = self.aircraft_params['eta_climb'] # Climb efficiency
        self.eta_cruise = self.aircraft_params['eta_cruise'] # Cruise efficiency
        self.atmosphere_condition = self.aircraft_params['atmosphere_condition']   

        self.stall_speed = self.compute_stall_speed()

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
        self.soc_required_to_complete_mission = 30 # TODO: Complete calc_soc_required_for_flight function
        self.target_soc_constant = self.aircraft_params['target_soc_constant']
        self.velocity_optimizer = VelocityOptimizer(aircraft_params=self.aircraft_params)
        # logfile = set_logfile_path(log_file_name='main', output_folder_path=output_folder_path)
        # self.logger = setup_logger(name='main', log_file=logfile, env=self.env)
        self.logger = logger
        self.aircraft_logger = aircraft_logger

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
        self._soc += round(value, 2)

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
    def vertical_velocity(self):
        return self._vertical_velocity
    
    @vertical_velocity.setter
    def vertical_velocity(self, value):
        self._vertical_velocity = value

    # @property
    # def altitude(self):
    #     return self._altitude
    
    # @altitude.setter
    # def altitude(self, value):
    #     if self._altitude <= 0:
    #         self._altitude = 0
    #     else:
    #         self._altitude = value

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

    def __str__(self):
        return f"Aircraft {self.tail_number}:\n" \
            f"  - Origin: {self.origin_vertiport_id}\n" \
            f"  - Destination: {self.destination_vertiport_id}\n" \
            f"  - Passengers: {self.passengers_onboard}\n" \
            f"  - SOC: {round(self.soc, 2)}%\n" \
            f"  - Arrival Time: {self.arrival_time}\n" \
            f"  - Departure Time: {self.departure_time}\n" \
            f"  - Location: {self.location}\n" \
            f"  - Serviced Time at Location: {self.serviced_time_at_the_location}\n"
    
    def compute_stall_speed(self):
            return stall_speed(atmosphere_condition=self.atmosphere_condition,
                               altitude=self.altitude,
                               mtom=self.mtom,
                               wing_area=self.wing_area,
                               cl_max=self.cl_max)
    
    def compute_air_speed(self, origin: str, 
                          destination: str, 
                          horizontal_speed: float, 
                          vertical_velocity: float) -> tuple[float, float]:
        horizontal_travel_time = self.compute_travel_time_from_horizontal_velocity(
            origin=origin, destination=destination, horizontal_speed=horizontal_speed)
        
        vertical_travel_time = self.compute_travel_time_from_vertical_velocity(
            origin=origin, destination=destination, vertical_velocity=vertical_velocity)

        return self.adjust_speeds_based_on_travel_time(
            origin, destination, horizontal_speed, horizontal_travel_time, vertical_velocity, vertical_travel_time)
        
    def adjust_speeds_based_on_travel_time(self, 
                                           origin, 
                                           destination, 
                                           horizontal_speed, 
                                           horizontal_travel_time, 
                                           vertical_velocity, 
                                           vertical_travel_time):
        if horizontal_travel_time > vertical_travel_time:
            power_consumption_for_lift = climb_power_consumption_for_lift(tom=self.tom, vertical_velocity=vertical_velocity)
            power_consumption_for_drag = climb_power_consumption_for_drag(altitude=self.altitude,
                                                                          atmosphere_condition=self.atmosphere_condition,
                                                                          wing_area=self.wing_area,
                                                                          cd_0=self.cd_0,
                                                                          ld_max=self.ld_max,
                                                                          tom=self.tom,
                                                                          horizontal_speed=horizontal_speed)
            if power_consumption_for_lift >= power_consumption_for_drag:
                # Reduce vertical speed
                return self.adjust_speeds_for_vertical_travel_time(
                    origin,
                    destination,
                    horizontal_speed,
                    horizontal_travel_time,
                )
            else:
                # Increase horizontal speed
                return self.adjust_speeds_for_horizontal_travel_time(
                    origin,
                    destination,
                    horizontal_speed,
                    vertical_velocity,
                    horizontal_travel_time,
                    vertical_travel_time
                )
        elif horizontal_travel_time < vertical_travel_time:
            # Increase horizontal speed
            return self.adjust_speeds_for_horizontal_travel_time(
                origin,
                destination,
                horizontal_speed,
                vertical_velocity,
                horizontal_travel_time,
                vertical_travel_time
            )
        else:
            return horizontal_speed, vertical_velocity

    def adjust_speeds_for_vertical_travel_time(self, origin, destination, horizontal_speed, horizontal_travel_time):
        vertical_velocity = self.compute_vertical_velocity_from_time(
            origin=origin,
            destination=destination,
            time=horizontal_travel_time)
        return horizontal_speed, vertical_velocity

    def adjust_speeds_for_horizontal_travel_time(self, origin, destination, horizontal_speed, vertical_velocity, horizontal_travel_time, vertical_travel_time):
        horizontal_speed = self.compute_horizontal_speed_from_time(
            origin=origin,
            destination=destination,
            time=vertical_travel_time
        )

        if horizontal_speed > self.max_horizontal_velocity:
            horizontal_speed = self.max_horizontal_velocity
            vertical_velocity = self.compute_vertical_velocity_from_time(
                origin=origin,
                destination=destination,
                time=horizontal_travel_time
            )
        return horizontal_speed, vertical_velocity    

    def compute_travel_time_from_horizontal_velocity(self, origin: str, destination: str, horizontal_speed: float) -> float:
        """
        Computes the travel time between two locations given the horizontal speed in m/s. Returns the travel time in secs.
        """
        distance = self.vertiport_manager.airspace.waypoint_distances[origin][destination]
        return round(distance / horizontal_speed)
    
    def compute_horizontal_speed_from_time(self, origin: str, destination: str, time: float) -> float:
        """
        Computes the horizontal speed between two locations given the travel time in secs. Returns the horizontal speed in m/s.
        """
        distance = self.vertiport_manager.airspace.waypoint_distances[origin][destination]
        horizontal_speed = round(distance / time)
        if horizontal_speed > self.max_horizontal_velocity:
            return self.max_horizontal_velocity
        else:
            return horizontal_speed
    
    def compute_travel_time_from_vertical_velocity(self, origin: str, destination: str, vertical_velocity: float) -> float:
        """
        Computes the travel time between two locations given the vertical speed in m/s.
        """
        origin_altitude = self.get_node_altitude(origin)
        destination_altitude = self.get_node_altitude(destination)
        altitude_difference = abs(destination_altitude - origin_altitude)
        return round(altitude_difference / vertical_velocity)

    def compute_vertical_velocity_from_time(self, origin: str, destination: str, time: float) -> float:
        """
        Computes the vertical speed between two locations given the travel time in secs. Returns the vertical speed in m/s.
        """
        origin_altitude = self.get_node_altitude(origin)
        destination_altitude = self.get_node_altitude(destination)
        altitude_difference = abs(destination_altitude - origin_altitude)
        return round(altitude_difference / time)
                                                                                        
    def aircraft_landing_process(self):
        final_approach_fix = self.vertiport_manager.get_second_to_last_airlink_node_id(flight_direction=self.flight_direction)
        self.setup_for_descend(final_approach_fix)
        yield self.env.process(self.descend_to_final_approach_fix(final_approach_fix))
        yield self.env.process(self.descend_transition())
        yield self.env.process(self.hover_descend())
        yield self.env.process(self.post_landing_procedures())

    def guess_initial_velocity(self):
        return [self.speed, np.mean([self.vertical_velocity, self.max_vertical_velocity])]

    def setup_for_descend(self, final_approach_fix):
        horizontal_distance, vertical_distance = self.horizontal_and_vertical_distance(self.location, final_approach_fix)
        initial_velocity_guess = self.guess_initial_velocity()
        self.speed, self.vertical_velocity = self.velocity_optimizer.optimize(
                                                V=initial_velocity_guess,
                                                tom=self.tom,
                                                altitude=self.altitude,
                                                horizontal_distance=horizontal_distance,
                                                vertical_distance=vertical_distance,
                                                cost_type='descend'
                                                )
        self.state = 'descend'

        self.aircraft_logger.debug(f'Descend Setup: Aircraft {self.tail_number} will descend from {self.location} to {final_approach_fix}'
                                  f' with forward velocity {self.speed} and vertical velocity {self.vertical_velocity}, SOC: {round(self.soc, 2)}.'
                                  f' Horizontal distance: {horizontal_distance}, vertical distance: {vertical_distance}')

    def descend_to_final_approach_fix(self, final_approach_fix):      
        descend_time = self.compute_travel_time_from_horizontal_velocity(origin=self.location,
                                                                      destination=final_approach_fix,
                                                                      horizontal_speed=self.speed)
        descend_energy_consumption = round(self.descend_energy_consumption(velocity=self.speed,
                                                                    descend_end_altitude=self.get_node_altitude(final_approach_fix),
                                                                    descend_time=descend_time), 2)
        self.total_energy_consumption += descend_energy_consumption
        yield self.env.timeout(sec_to_ms(descend_time))
          
        self.update_aircraft_state(final_approach_fix, descend_energy_consumption, 'final_approach_fix_arrival')
        yield self.env.process(self.vertiport_manager.fato_pad_request(aircraft=self, operation_type='arrival'))

        self.aircraft_logger.debug(f'Descend: Aircraft {self.tail_number} has arrived at {final_approach_fix} with forward velocity {self.speed} and vertical velocity {self.vertical_velocity}, SOC: {round(self.soc, 2)}.'
                                  f' Descend time: {descend_time}, descend energy consumption: {descend_energy_consumption}.')

    def descend_transition(self):
        self.state = 'descend_transition'
        hover_fix_id = self.vertiport_manager.get_last_airlink_node_id(flight_direction=self.flight_direction)
        horizontal_distance, vertical_distance = self.horizontal_and_vertical_distance(self.location, hover_fix_id)
        initial_velocity_guess = self.guess_initial_velocity()
        self.speed, self.vertical_velocity = self.velocity_optimizer.optimize(
                                                V=initial_velocity_guess,
                                                tom=self.tom,
                                                altitude=self.altitude,
                                                horizontal_distance=horizontal_distance,
                                                vertical_distance=vertical_distance,
                                                cost_type='descend_transition'
                                                )
        # Descend speed is zero at the end of the descend transition. So, we get the average speed.
        descend_transition_time = round(horizontal_distance/self.speed) * 2
        descend_transition_energy_consumption = round(self.descend_transition_energy_consumption(velocity=round(self.speed/2),
                                                                                        descend_transition_end_altitude=self.get_node_altitude(hover_fix_id),
                                                                                        descend_transition_time=descend_transition_time), 2)
        self.total_energy_consumption += descend_transition_energy_consumption
        yield self.env.timeout(sec_to_ms(descend_transition_time))

        self.aircraft_logger.debug(f'Descend Transition: Aircraft {self.tail_number} has arrived at {hover_fix_id} with forward velocity {self.speed} and vertical velocity {self.vertical_velocity}, SOC: {round(self.soc, 2)}.'
                                    f' Descend transition time: {descend_transition_time}, descend transition energy consumption: {descend_transition_energy_consumption}.')

        self.speed = 0
        self.update_aircraft_state(hover_fix_id, descend_transition_energy_consumption, 'hover_fix_arrival')
        self.vertiport_manager.release_fix_resource(aircraft=self, operation='arrival')

    def hover_descend(self):
        self.state = 'hover_descend'
        self.vertical_velocity = self.aircraft_params['vertical_landing_velocity']
        hover_descend_time = self.compute_travel_time_from_vertical_velocity(origin=self.location,
                                                        destination=self.assigned_fato_id,
                                                        vertical_velocity=self.vertical_velocity)
        hover_descend_time += ms_to_sec(self.time_rotor_spin_down)
        yield self.env.timeout(sec_to_ms(hover_descend_time))
        hover_descend_energy_consumption = round(self.vertical_takeoff_landing_energy_consumption(fato_altitude=self.get_node_altitude(self.assigned_fato_id),
                                                                                            hover_altitude=self.get_node_altitude(self.location),
                                                                                            hover_time=hover_descend_time,
                                                                                            operation='landing'), 2)
        self.total_energy_consumption += hover_descend_energy_consumption

        self.aircraft_logger.debug(f'Hover Descend: Aircraft {self.tail_number} has arrived at {self.assigned_fato_id} with forward velocity {self.speed} and vertical velocity {self.vertical_velocity}, SOC: {round(self.soc, 2)}.'
                                    f' Hover descend time: {hover_descend_time}, hover descend energy consumption: {hover_descend_energy_consumption}.')

        self.vertical_velocity = 0
        self.update_aircraft_state(self.assigned_fato_id, hover_descend_energy_consumption, 'landed')
        self.event_saver.update_aircraft_energy_consumption_tracker(flight_direction=self.flight_direction, energy_consumption=self.total_energy_consumption)
        self.logger.debug(f'Landed: Aircraft {self.tail_number} landed at {self.destination_vertiport_id} with SOC: {round(self.soc, 2)}, flight duration: {ms_to_min(self.flight_duration)}, holding time: {ms_to_min(self.holding_time)} mins, total energy consumption: {round(self.total_energy_consumption, 2)}')
        self.aircraft_logger.debug(f'Landed: Aircraft {self.tail_number} landed at {self.destination_vertiport_id} with SOC: {round(self.soc, 2)}, flight duration: {ms_to_min(self.flight_duration)}, holding time: {self.holding_time}, total energy consumption: {self.total_energy_consumption}')
        self.total_energy_consumption = 0
        self.idle_time = 0
         # TODO: Remove below. HARDCODED for optimization integration
        if self.flight_direction == 'LAX_DTLA':
            self.soc = self.preflight_soc - 10
        elif self.flight_direction == 'DTLA_LAX':
            self.soc = self.preflight_soc - 7.5
        else:
            raise ValueError(f'Invalid flight direction: {self.flight_direction}')

    def post_landing_procedures(self):
        yield self.env.timeout(round(self.time_post_landing_safety_checks))
        yield self.env.timeout(round(self.time_tug_connection))
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='ready_for_taxi_in')
        self.arrival_time = self.env.now
        self.save_flight_duration()
        self.aircraft_logger.debug(f'Post Landing Procedures: Aircraft {self.tail_number} has completed post landing procedures at {self.destination_vertiport_id} with SOC: {round(self.soc, 2)}.')

    def update_aircraft_state(self, location, energy_consumption, event):
        self.soc_discharge_update(energy_consumption)
        self.altitude = self.get_node_altitude(location)
        self.location = location
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event=event)

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
            self.departure_time = self.env.now
        # Check whether the vertiport has a parking pad or not. If it has a parking pad then the aircraft will taxi. Otherwise, it will be parked on the FATO pad.
        if len(taxi_route) == 0:
            if operation_type == 'arrival':
                # Decrease the aircraft arrival queue counter
                self.event_saver.update_aircraft_arrival_queue_counter(vertiport_id=vertiport_id,
                                                                       queue_update=-1)     
                self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='parked_on_fato_pad')
            return                          

        self.state = 'taxiing'
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

        self.state = 'parked'


    def aircraft_take_off_process(self, take_off_fato_id):
        """Defines the take-off process of an aircraft."""
        self.preflight_soc = self.soc
        yield self.env.process(self.initial_takeoff_procedure(take_off_fato_id))
        yield self.env.process(self.hover_climb())
        yield self.env.process(self.climb_transition())
        self.release_fato_and_departure_fix()
        yield self.env.process(self.climb_to_cruise_altitude())

    def initial_takeoff_procedure(self, take_off_fato_id):
        """Initial takeoff procedures, including updating location, departure time and passenger records."""
        self.location = take_off_fato_id
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='fato_arrival')

        for passenger in self.passengers_onboard:
            passenger.departure_time = self.env.now    
            self.event_saver.save_agent_state(agent=passenger, agent_type='passenger', event='fato_arrival')    

        yield self.env.timeout(round(self.time_tug_disconnection))
        yield self.env.timeout(round(self.time_pre_take_off_check_list))
        self.turnaround_time = self.env.now - self.arrival_time
        self.logger.debug(f'TakeOff: Aircraft {self.tail_number} took off from vertiport {self.origin_vertiport_id} to {self.destination_vertiport_id} at SOC: {round(self.soc, 2)} with {len(self.passengers_onboard)} passengers onboard')
        self.aircraft_logger.debug(f'TakeOff: Aircraft {self.tail_number} ready for takeoff from vertiport {self.origin_vertiport_id} to {self.destination_vertiport_id} at SOC: {round(self.soc, 2)} with {len(self.passengers_onboard)} passengers onboard')

    def hover_climb(self):
        """Hover climb phase of the takeoff."""
        self.state = 'hover_climb'
        self.speed = 0 # horizontal speed
        self.vertical_velocity = self.aircraft_params['vertical_takeoff_velocity']
        hover_fix_id = self.vertiport_manager.get_first_airlink_node_id(flight_direction=self.flight_direction)
        hover_climb_time = self.compute_travel_time_from_vertical_velocity(origin=self.location,
                                                                           destination=hover_fix_id,
                                                                           vertical_velocity=self.vertical_velocity)
        hover_climb_time += ms_to_sec(self.time_rotor_spin_up)
        hover_climb_energy_consumption = round(self.vertical_takeoff_landing_energy_consumption(fato_altitude=self.get_node_altitude(self.location),
                                                                                        hover_altitude=self.get_node_altitude(hover_fix_id),
                                                                                        hover_time=hover_climb_time,
                                                                                        operation='takeoff'), 2)
        self.total_energy_consumption += hover_climb_energy_consumption
        yield self.env.timeout(sec_to_ms(hover_climb_time))

        self.aircraft_logger.debug(f'Hover Climb: Aircraft {self.tail_number} has arrived at {hover_fix_id} with forward velocity {self.speed} and'
                                  f' vertical velocity {self.vertical_velocity}, SOC: {round(self.soc, 2)}. Hover climb time: {hover_climb_time},'
                                    f' hover climb energy consumption: {hover_climb_energy_consumption}.')

        self.update_aircraft_state(hover_fix_id, hover_climb_energy_consumption, 'hover_climb_end')

    def climb_transition(self):
        """Climb transition phase of the takeoff."""
        self.state = 'climb_transition'
        departure_fix_id = self.vertiport_manager.get_second_airlink_node_id(flight_direction=self.flight_direction)
        horizontal_distance, vertical_distance = self.horizontal_and_vertical_distance(self.location, departure_fix_id)
        initial_velocity_guess = self.guess_initial_velocity()
        self.speed, self.vertical_velocity = self.velocity_optimizer.optimize(
                                                V=initial_velocity_guess,
                                                tom=self.tom,
                                                altitude=self.altitude,
                                                horizontal_distance=horizontal_distance,
                                                vertical_distance=vertical_distance,
                                                cost_type='climb_transition')

        # The speed is averaged because aircraft don't have forward velocity at the beginning of the climb transition phase
        climb_transition_time = round(horizontal_distance / self.speed) * 2
        climb_transition_energy_consumption = round(self.climb_transition_energy_consumption(velocity=round(self.speed/2, 2),
                                                                                    climb_transition_end_altitude=self.get_node_altitude(departure_fix_id),
                                                                                    climb_transition_time=climb_transition_time), 2)
        self.total_energy_consumption += climb_transition_energy_consumption

        yield self.env.timeout(sec_to_ms(climb_transition_time))

        self.aircraft_logger.debug(f'Climb Transition: Aircraft {self.tail_number} has arrived at {departure_fix_id} with forward velocity {self.speed} and'
                                    f' vertical velocity {self.vertical_velocity}, SOC: {round(self.soc, 2)}. Climb transition time: {climb_transition_time},'
                                        f' climb transition energy consumption: {climb_transition_energy_consumption}.')
        
        self.update_aircraft_state(departure_fix_id, climb_transition_energy_consumption, 'climb_transition_end')

    def release_fato_and_departure_fix(self):
        """Releasing FATO and departure fix."""
        self.assigned_fato_resource.fato_resource.release(self.aircraft_fato_usage_request)
        self.assigned_fato_id = None
        self.assigned_fato_resource = None
        self.event_saver.update_fato_usage_tracker(vertiport_id=self.origin_vertiport_id,
                                                fato_usage=-1)  
        self.vertiport_manager.release_fix_resource(aircraft=self, operation='departure')

    def climb_to_cruise_altitude(self):
        """Climbing to cruise altitude phase."""
        self.state = 'climb'
        first_waypoint = self.vertiport_manager.get_third_airlink_node_id(flight_direction=self.flight_direction)
        first_waypoint_resource = self.vertiport_manager.get_third_airlink_resource(flight_direction=self.flight_direction)
        horizontal_distance, vertical_distance = self.horizontal_and_vertical_distance(self.location, first_waypoint)
        initial_velocity_guess = self.guess_initial_velocity()
        self.speed, self.vertical_velocity = self.velocity_optimizer.optimize(
                                                V=initial_velocity_guess,
                                                tom=self.tom,
                                                altitude=self.altitude,
                                                horizontal_distance=horizontal_distance,
                                                vertical_distance=vertical_distance,
                                                cost_type='climb')
        climb_time = round(horizontal_distance / self.speed)
        with first_waypoint_resource.request() as req:
            yield req
            yield self.env.timeout(sec_to_ms(climb_time))
        climb_energy_consumption = round(self.climb_energy_consumption(velocity=self.speed,
                                                                climb_end_altitude=self.get_node_altitude(first_waypoint),
                                                                climb_time=climb_time), 2)
        self.total_energy_consumption += climb_energy_consumption

        self.aircraft_logger.debug(f'Climb: Aircraft {self.tail_number} has arrived at {first_waypoint} with forward velocity {self.speed} and'
                                    f' vertical velocity {self.vertical_velocity}, SOC: {round(self.soc, 2)}. Climb time: {climb_time},'
                                        f' climb energy consumption: {climb_energy_consumption}.')

        self.update_aircraft_state(first_waypoint, climb_energy_consumption, 'climb_end')
        self.vertical_velocity = 0

    def fly_in_the_airspace(self, user_modification=False):
        """
        Finds the location of the aircraft in the airspace from self.vertiport_manager.airspace.airlink_resources
        and traverses the airspace starting from that location        
        """      
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

        # Start iterating the airlink resources from the next location. Second to last node is the final approach fix 
        # and the last node is th ehover fix. We don't request them here.
        if user_modification:
            starting_index = current_location_index
        else:
            starting_index = current_location_index + 1
        for waypoint_id, resource in list(airlink_resources.items())[starting_index:-2]:
            with resource.request() as req:
                yield req
                # Compute the horizontal and vertical distance between the current location and the next waypoint
                horizontal_distance, vertical_distance = self.horizontal_and_vertical_distance(self.location, waypoint_id)
                # If the vertical distance is not zero, then the aircraft is climbing or descending. If the previous flight phase
                # is not cruise, then the aircraft is climbing. Otherwise, the aircraft is descending.
                if vertical_distance != 0 and self.state == 'climb':
                    initial_velocity_guess = self.guess_initial_velocity()
                    self.speed, self.vertical_velocity = self.velocity_optimizer.optimize(
                                                            V=initial_velocity_guess,
                                                            tom=self.tom,
                                                            altitude=self.altitude,
                                                            horizontal_distance=horizontal_distance,
                                                            vertical_distance=vertical_distance,
                                                            cost_type='climb')
                    climb_time = round(horizontal_distance / self.speed)
                    yield self.env.timeout(round(sec_to_ms(climb_time)))
                    energy_consumption = round(self.climb_energy_consumption(velocity=self.speed,
                                                                            climb_end_altitude=self.get_node_altitude(waypoint_id),
                                                                            climb_time=climb_time), 2)
                    self.total_energy_consumption += energy_consumption  

                    self.aircraft_logger.debug(f'Continue Climb: Aircraft {self.tail_number} has arrived at {waypoint_id} with forward velocity {self.speed} and'
                                                f' vertical velocity {self.vertical_velocity}, SOC: {round(self.soc, 2)}. Climb time: {climb_time},'
                                                    f' climb energy consumption: {energy_consumption}.')
                # If the vertical distance is not zero and the previous flight phase is cruise or descend, then the aircraft is descending.
                elif vertical_distance != 0 and self.state in ['descend', 'cruise']:
                    self.state = 'descend'
                    initial_velocity_guess = self.guess_initial_velocity()
                    self.speed, self.vertical_velocity = self.velocity_optimizer.optimize(
                                                            V=initial_velocity_guess,
                                                            tom=self.tom,
                                                            altitude=self.altitude,
                                                            horizontal_distance=horizontal_distance,
                                                            vertical_distance=vertical_distance,
                                                            cost_type='descend')
                    descend_time = round(horizontal_distance / self.speed)
                    yield self.env.timeout(sec_to_ms(descend_time))
                    energy_consumption = round(self.descend_energy_consumption(velocity=self.speed,
                                                                            descend_end_altitude=self.get_node_altitude(waypoint_id),
                                                                            descend_time=descend_time), 2)
                    self.total_energy_consumption += energy_consumption 

                    self.aircraft_logger.debug(f'Descend: Aircraft {self.tail_number} has arrived at {waypoint_id} with forward velocity {self.speed} and'
                                                  f' vertical velocity {self.vertical_velocity}, SOC: {round(self.soc, 2)}. Descend time: {descend_time},'
                                                        f' descend energy consumption: {energy_consumption}.')               
                else:
                    # If the vertical distance is zero, then the aircraft is in cruise
                    self.state = 'cruise'
                    if self.aircraft_params['cruise_velocity']:
                        self.speed = self.aircraft_params['cruise_velocity'] 
                    else:                   
                        self.speed = self.velocity_optimizer.max_range_speed(altitude=self.altitude, tom=self.tom)
                    link_traversal_time = self.compute_travel_time_from_horizontal_velocity(origin=self.location, 
                                                                                        destination=waypoint_id, 
                                                                                        horizontal_speed=self.speed)
                    yield self.env.timeout(sec_to_ms(link_traversal_time))
                    # Compute energy consumption
                    energy_consumption = round(self.cruise_energy_consumption(velocity=self.speed, time_cruise=link_traversal_time), 2)
                    self.total_energy_consumption += energy_consumption
            
                    self.aircraft_logger.debug(f"Aircraft {self.tail_number} V_h: {self.speed}, V_v velocity: {self.vertical_velocity}, time: {link_traversal_time},"
                                            f" energy consumption: {energy_consumption} during {self.state} from {self.location} to {waypoint_id}. SOC: {round(self.soc, 2)}")
                    
            self.update_aircraft_state(waypoint_id, energy_consumption, 'cruise')         

        yield self.env.process(self.vertiport_manager.simulate_terminal_airspace_arrival_process(
            aircraft=self, arriving_passengers=self.passengers_onboard)
        )

    # ==================== CHARGING METHODS ====================
    def request_charger(self):
        """
        This method is used when the charger configuration is normal (any parking pads can use any chargers).
        Returns the charger resource that is used by the aircraft and the charging request.
        """
        used_charger_resource = self.vertiport_manager.vertiports[self.destination_vertiport_id].charger_resource
        return used_charger_resource, used_charger_resource.request()

    def get_charging_time(self):
        """
        Get charging time - Two options: Constant charging time or draw a number from distribution
        """
        if self.time_charging is not None:
            return max(self.time_passenger_embark_disembark, self.time_charging)
        elif self.target_soc:
            charge_time = self.get_charge_time_from_soc(init_soc=self.soc, target_soc=self.target_soc)
            charge_time = roundup_to_five_minutes(charge_time)
        elif self.target_soc_constant:
            charge_time = self.get_charge_time_from_soc(init_soc=self.soc, target_soc=self.target_soc_constant)
        else:
            charge_time = sec_to_ms(self.vertiport_manager.charging_time_distribution.pick_number_from_distribution())
            charge_time = max(self.time_passenger_embark_disembark, charge_time)

        self.event_saver.save_aircraft_charging_time(vertiport_id=self.destination_vertiport_id,
                                                     aircraft_id=self.tail_number, 
                                                     charging_time=charge_time)
        self.logger.debug(f"Started Charging: Aircraft {self.tail_number} will charge for {round(ms_to_sec(charge_time)/60,2)} mins at {self.destination_vertiport_id}. init_soc: {round(self.soc, 2)}, target_soc: {self.target_soc}")
        
        return charge_time

    def charge_aircraft(self, parking_space: object, shared_charger: bool = False) -> None:
        """
        If the charger configuration is fixed and share-limited, all of the chargers that a parking pad has access
        should be requested. We use chargers as a resource instead of simpy.Store or simpy.Filterstore because it's
        easier to follow which resource is being used by which aircraft.
        """
        if not self.target_soc and self.soc >= self.soc_required_to_complete_mission:
            self.set_charging_time_trackers()
            self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='no_charge_needed')
            # After deboarding the passengers aircraft will be ready for the next flight.
            yield self.env.timeout(round(self.time_passenger_embark_disembark))
            return
        
        # If the chargers are shared, request all of the chargers that the parking pad has access to.
        if shared_charger:
            used_charger_resource, selected_charging_request = self.handle_shared_charger(parking_space)
        else:
            used_charger_resource, selected_charging_request = self.request_charger()
            yield selected_charging_request

        self.start_charging_process()
        self.idle_time += self.env.now - self.ground_holding_end_time 
        self.state = 'charging'
        yield self.env.timeout(round(self.get_charging_time()))
        self.state = 'idle'
        self.end_charging_process()
        old_soc = self.soc
        self.soc_charge_update()
        # Reset the target_soc to None for the next flight
        self.set_target_soc_none()
        self.release_charger_resource(used_charger_resource, selected_charging_request)
        self.logger.debug(f"Finished Charging: Aircraft {self.tail_number} at {self.destination_vertiport_id}. Previous SoC: {round(old_soc, 2)}, New SoC: {round(self.soc, 2)}")

    def set_charging_time_trackers(self):
        self.charging_start_time = self.env.now
        self.charging_end_time = self.env.now

    def set_target_soc_none(self):
        self.target_soc = None

    def handle_shared_charger(self, parking_space: object):
        charger_requests = self.env.process(self.request_all_chargers(parking_space))
        charging_requests_list = self.get_first_filled_charger_request(charger_requests)
        selected_charging_request = charging_requests_list[0]
        used_charger_resource = get_key_from_value(charger_requests, selected_charging_request)
        # Find which charger request is being used
        self.release_unused_charger_resources(charger_requests, used_charger_resource, charging_requests_list)
        return used_charger_resource, selected_charging_request

    def request_all_chargers(self, parking_space: object):
        # Request all of the chargers that the parking pad has access.
        charger_requests = {charger: charger.request() for charger in parking_space.charger_resources}
        # Yield all of the charger requests. When any_of used it fires all of the requests.
        yield self.env.any_of(list(charger_requests.values()))
        return charger_requests

    def get_first_filled_charger_request(self, charger_requests: dict):
        # The selected charging request is the on top of the list
        return list(charger_requests.keys())

    def release_unused_charger_resources(self, charger_requests: dict, used_charger_resource: object, charging_requests_list: object):
        # Since any_of() used more than one request might be filled. Only one should be kept and the rest should be canceled.        
        for charger_res, charger_req in charger_requests.items():
            if charger_res != used_charger_resource:
                if len(charging_requests_list) > 1:
                    charger_res.release(charger_req)
                else:
                    charger_req.cancel()

    def start_charging_process(self):
        self.charging_start_time = self.env.now
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='charging_start')

    def end_charging_process(self):
        self.charging_end_time = self.env.now
        self.event_saver.save_agent_state(agent=self, agent_type='aircraft', event='charging_end')

    def release_charger_resource(self, used_charger_resource: object, selected_charging_request: object):
        used_charger_resource.release(selected_charging_request)

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
        initial_soc_time = df[df.soc == round(initial_soc)]['time_sec'].values[0]
        # Get the time at final soc level
        final_soc_time = initial_soc_time + ms_to_sec(charge_time)
        # Get the soc at final soc level
        idx_final_soc = df['time_sec'].sub(final_soc_time).abs().idxmin()
        return df.loc[idx_final_soc]['soc']

    def get_charge_time_from_soc(self, init_soc: int, target_soc: int) -> float:
        """
        Calculates the charge time required to reach the target soc level.

        Parameters
        ----------
        init_soc: int
            Initial soc level of the aircraft.
        target_soc: int
            Target soc level of the aircraft.

        Returns
        -------
        float
            Charge time required to reach the target soc level.
        """
        check_magnitude_order(init_soc, target_soc)
        df = self.vertiport_manager.aircraft_battery_models[self.destination_vertiport_id]
        init_soc_time = df[df.soc == round(init_soc)]['time_sec'].values[0]
        target_soc_time = df[df.soc == target_soc]['time_sec'].values[0]
        return sec_to_ms(target_soc_time - init_soc_time)

    def soc_charge_update(self) -> None:
        """
        Updates the charge level of the aircraft using current charge time.
        """
        charge_time = self.env.now - self.charging_start_time
        charge_lookup_table = self.vertiport_manager.aircraft_battery_models[self.destination_vertiport_id]
        final_soc = Aircraft.calc_soc_from_charge_time(charge_time=charge_time, initial_soc=self.soc, df=charge_lookup_table)
        self._soc = self.target_soc
        # self._soc = min(100, final_soc)

    def convert_kwh_soc(self, kwh: float) -> int:
        """
        Converts kwh to aircraft's soc level.
        """
        return round(kwh / self.battery_capacity * 100, 2)
    
    def soc_discharge_update(self, kwh: float) -> None:
        """
        Updates the charge level of the aircraft using current charge time.
        """
        self.aircraft_logger.debug(f"Discharging {kwh} kwh from aircraft {self.tail_number} at {self.location}"
                                  f" during {self.state}, SOC: {round(self.soc, 2)}")
        if self.soc-self.convert_kwh_soc(kwh) < 0:
            soc_update = self.soc
            print(f"Warning: Aircraft {self.tail_number}'s SOC is less than 0. SOC: {round(self.soc, 2)}, at time: {self.env.now} during {self.state} at {self.location}")
        else:
            soc_update = self.convert_kwh_soc(kwh)
        self.update_soc(-soc_update)
        self.aircraft_logger.debug(f"Discharged {kwh} kwh from aircraft {self.tail_number} at {self.location}"
                                    f" during {self.state}, new SOC: {round(self.soc, 2)}")
        self.check_reserve_energy()

    def unload_passengers(self, passenger_disembark_time):
        # TODO: check
        yield self.env.timeout(round(passenger_disembark_time))
        self.event_saver.aircraft_dict[self.tail_number]['passenger_unloading_finished'] = \
            timestamp_to_datetime(self.event_saver.sim_start_timestamp, self.env.now)

    # ================= ENERGY CONSUMPTION METHODS ====================

    def vertical_takeoff_landing_energy_consumption(self, fato_altitude: float, hover_altitude, hover_time: float, operation: str) -> float:
        self.tom = self.compute_flight_mass() # Takeoff mass
        vertical_takeoff_landing_power = vertical_takeoff_landing_phase_power(start_altitude=fato_altitude,
                                                                              end_altitude=hover_altitude,
                                                                              aircraft_params=self.aircraft_params,
                                                                              tom=self.tom,
                                                                              vertical_velocity=self.vertical_velocity)
        vertical_takeoff_landing_power = watt_to_kw(vertical_takeoff_landing_power)

        if operation == 'takeoff':
            return sec_to_hr(vertical_takeoff_landing_power * hover_time) # kWh - time units need to be seconds
        elif operation == 'landing':
            return sec_to_hr(vertical_takeoff_landing_power * hover_time)
        else:
            raise ValueError('operation must be either takeoff or landing')


    def climb_transition_energy_consumption(self, velocity: float, 
                                            climb_transition_end_altitude: float,
                                            climb_transition_time: float) -> float:
        climb_transition_power = climb_transition_phase_power(start_altitude=self.altitude, 
                                                              end_altitude=climb_transition_end_altitude, 
                                                              aircraft_params=self.aircraft_params, 
                                                              tom=self.tom, 
                                                              vertical_velocity=self.vertical_velocity, 
                                                              velocity=velocity)
        climb_transition_power = watt_to_kw(climb_transition_power)

        return sec_to_hr(climb_transition_power * climb_transition_time)
    
    def descend_transition_energy_consumption(self, velocity: float, 
                                              descend_transition_end_altitude: float, 
                                              descend_transition_time: float) -> float:
        """
        Computes the energy consumption during the descend transition phase.
        :param velocity: Velocity (m/s)
        :param descend_transition_end_altitude: Altitude at the end of the descend transition phase (meters)
        :param descend_transition_time: Time spent in the descend transition phase (seconds)
        :return: Energy consumption during the descend transition phase (kWh)
        """
        descend_transition_power = descend_transition_phase_power(start_altitude=self.altitude,
                                                                  end_altitude=descend_transition_end_altitude,
                                                                  aircraft_params=self.aircraft_params,
                                                                  tom=self.tom,
                                                                  vertical_velocity=self.vertical_velocity,
                                                                  velocity=velocity)
        descend_transition_power = watt_to_kw(descend_transition_power)

        return sec_to_hr(descend_transition_power * descend_transition_time)

    def climb_energy_consumption(self, velocity: float, climb_end_altitude: float, climb_time: float) -> float:
        climb_power = climb_phase_power(start_altitude=self.altitude, 
                                        end_altitude=climb_end_altitude, 
                                        aircraft_params=self.aircraft_params, 
                                        tom=self.tom, 
                                        vertical_velocity=self.vertical_velocity, 
                                        velocity=velocity)
        climb_power = watt_to_kw(climb_power)

        return sec_to_hr(climb_power * climb_time)
    
    def descend_energy_consumption(self, velocity: float, descend_end_altitude: float, descend_time: float) -> float:
        """
        Computes the energy consumption during the descent phase of the mission.
        :param min_power_velocity: The minimum power speed of the aircraft in meters per second.
        :param descend_end_altitude: The altitude at which the descent ends in meters.
        :param descend_time: The time spent in the descent phase in seconds.
        :return: The energy consumption during the descent phase of the mission in kWh.
        """
        descend_power = descend_phase_power(start_altitude=self.altitude,
                                            end_altitude=descend_end_altitude,
                                            aircraft_params=self.aircraft_params,
                                            tom=self.tom,
                                            vertical_velocity=self.vertical_velocity,
                                            velocity=velocity)
        descend_power = watt_to_kw(descend_power)

        return sec_to_hr(descend_power * descend_time)
    
    def cruise_energy_consumption(self, velocity, time_cruise) -> float:
        cruise_velocity = min(self.input_cruise_speed, velocity)
        cruise_velocity = max(cruise_velocity, self.stall_speed)
        cruise_power = cruise_phase_power(cruise_velocity=cruise_velocity,
                                          aircraft_params=self.aircraft_params,
                                          tom=self.tom)
        cruise_power = watt_to_kw(cruise_power)
        return sec_to_hr(cruise_power * time_cruise)
    
    def update_holding_energy_consumption(self, time_holding) -> float:
        holding_power = cruise_phase_power(cruise_velocity=self.speed,
                                           aircraft_params=self.aircraft_params,
                                           tom=self.tom)
        holding_power = watt_to_kw(holding_power)
        holding_energy = ms_to_hr(holding_power * time_holding)
        self.soc_discharge_update(holding_energy)
    
    def check_reserve_energy(self) -> float:
        if self.soc <= 2 and self.state in ['landing', 'cruise', 'takeoff']:
            print(f"Aircraft {self.tail_number} is out of energy at time {self.env.now} while in {self.state} phase. The flight direction is {self.flight_direction} and it's location is {self.location}.")
        if self.soc <= 20 and self.state in ['landing', 'cruise', 'takeoff']:
            self.priority = 0

    def update_altitude(self, vertical_velocity, time):
        self.altitude += vertical_velocity * time
        self.altitude = max(self.altitude, 0)

    def compute_flight_mass(self, num_passenger= None) -> float:
        if num_passenger:
            return self.mtom - (self.aircraft_params['pax']-num_passenger)*self.aircraft_params['pax_mass']
        return self.mtom - (self.aircraft_params['pax']-len(self.passengers_onboard))*self.aircraft_params['pax_mass']

    def get_node_latitude(self, node_id) -> float:
        return self.vertiport_manager.node_locations[node_id][0]
    
    def get_node_longitude(self, node_id) -> float:
        return self.vertiport_manager.node_locations[node_id][1]
    
    def get_node_altitude(self, node_id) -> float:
        return self.vertiport_manager.node_locations[node_id][2]
    
    def get_altitude_difference(self, node_id_1, node_id_2) -> float:
        """
        Returns the altitude difference between two nodes in meters.
        """
        return abs(self.get_node_altitude(node_id_1) - self.get_node_altitude(node_id_2))
    
    def get_horizontal_distance(self, node_id_1, node_id_2) -> float:
        """
        Returns the horizontal distance between two nodes in meters.
        """
        return self.vertiport_manager.airspace.waypoint_distances[node_id_1][node_id_2]

    def horizontal_and_vertical_distance(self, node_id_1, node_id_2) -> float:
        """
        Returns the horizontal and vertical distance between two nodes in meters.
        """
        return self.get_horizontal_distance(node_id_1, node_id_2), self.get_altitude_difference(node_id_1, node_id_2)
    
    def save_flight_duration(self):
        self.flight_duration = self.arrival_time - self.departure_time
        self.event_saver.update_flight_duration_tracker(flight_direction=self.flight_direction, flight_duration=self.flight_duration)


    
