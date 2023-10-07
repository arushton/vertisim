from .base_system_manager import BaseSystemManager
import simpy
from ..aircraft.aircraft import AircraftStatus
from typing import Dict, List, Any
from collections import defaultdict
from ..utils.units import sec_to_ms, ms_to_sec, ms_to_min, miles_to_m
from ..utils.helpers import get_random_process_id, miliseconds_to_hms, careful_round, duplicate_str

class RLSystemManager(BaseSystemManager):
    def __init__(self,
                 env: simpy.Environment,
                 vertiports: Dict,
                 vertiport_ids: List, 
                 num_initial_aircraft: int,                                 
                 scheduler: object,
                 wind: object,
                 airspace: object,
                 taxi_config: object,
                 sim_params: Dict,
                 aircraft_params: Dict,
                 vertiport_distances: Dict,
                 passenger_distributions: Dict,                 
                 event_saver: object,
                 node_locations: Dict,
                 logger: object,
                 aircraft_logger: object,
                 passenger_logger: object,
                 stopping_events: Dict
                 ):
        super().__init__(env=env,
                        vertiports=vertiports,
                        vertiport_ids=vertiport_ids,
                        num_initial_aircraft=num_initial_aircraft,
                        scheduler=scheduler,
                        wind=wind,
                        airspace=airspace,
                        taxi_config=taxi_config,
                        sim_params=sim_params,
                        aircraft_params=aircraft_params,
                        vertiport_distances=vertiport_distances,
                        passenger_distributions=passenger_distributions,
                        event_saver=event_saver,
                        node_locations=node_locations,
                        logger=logger,
                        aircraft_logger=aircraft_logger,
                        passenger_logger=passenger_logger
                        )
        
        self.average_flight_durations_per_od_pair = self._initialize_avg_flight_durations()
        self.stopping_events = stopping_events
    
    def reserve_aircraft(self, aircraft: object, destination_vertiport_id: str):
        # Start tracking aircraft allocation time
        aircraft_allocation_start_time = self.env.now
        # Update the vertiport flight request state
        self.vertiports[aircraft.origin_vertiport_id].num_flight_requests += 1           
        # Log the aircraft allocation process
        flight_id = get_random_process_id()
        self.logger.debug(f'|{flight_id}| Started: Aircraft allocation process at vertiport {aircraft.origin_vertiport_id} for {destination_vertiport_id}. Aircraft tail number: {aircraft.tail_number}')
        # Get the intended pushback time of the aircraft
        pushback_time = self.env.now             
        # Retrieve aircraft from the store
        aircraft = yield self.retrieve_aircraft(aircraft.origin_vertiport_id, aircraft.tail_number) 
        # Set the status of the aircraft
        aircraft.status = AircraftStatus.FLY      
        # Update the vertiport flight request state
        self.vertiports[aircraft.origin_vertiport_id].num_flight_requests -= 1    
        # Check the waiting room for additional passengers if there is still space on the aircraft
        departing_passengers = self.scheduler.collect_departing_passengers_by_od_vertiport(
            origin_vertiport_id=aircraft.origin_vertiport_id, destination_vertiport_id=destination_vertiport_id)                  
        # Set the real pushback time of the aircraft 
        aircraft.pushback_time = pushback_time
        # Set the flight direction of the aircraft
        aircraft.flight_direction = f'{aircraft.origin_vertiport_id}_{destination_vertiport_id}'
        # Set the flight ID of the aircraft
        aircraft.flight_id = flight_id
        # Measure and save the aircraft allocation time
        self.save_aircraft_allocation_time(aircraft.origin_vertiport_id, aircraft, aircraft_allocation_start_time)
        # Log the aircraft allocation process
        self.logger.debug(f'|{flight_id}| Completed: Aircraft allocation process at vertiport {aircraft.origin_vertiport_id} for {destination_vertiport_id}. Aircraft tail number: {aircraft.tail_number}, SOC: {careful_round(aircraft.soc, 2)}, Departing passengers: {len(departing_passengers)}')

        # Save aircraft allocation and idle times
        self.save_aircraft_times(aircraft)

        # Assign passengers to the aircraft
        aircraft.passengers_onboard = departing_passengers

        # Save total passenger waiting time and flight assignment time
        self.save_passenger_times(origin_vertiport_id=aircraft.origin_vertiport_id, passengers=aircraft.passengers_onboard) 
        self.passenger_logger.debug(f"Passenger waiting times for flight from {aircraft.origin_vertiport_id} to {destination_vertiport_id}: Passenger ids : {[p.passenger_id for p in departing_passengers]} waiting times: {[miliseconds_to_hms(self.env.now - passenger.waiting_room_arrival_time) for passenger in departing_passengers]}")

        # Start the passenger departure process
        if departing_passengers:
            self.logger.debug(f'|{flight_id}| Started: Passengers exited the waiting room at vertiport {aircraft.origin_vertiport_id} for {destination_vertiport_id} flight.')
            self.env.process(self.initiate_passenger_departure(departing_passengers=departing_passengers))
            self.logger.debug(f'|{flight_id}| Completed: Passengers arrived at the boarding gate at vertiport {aircraft.origin_vertiport_id} for {destination_vertiport_id} flight.')

        # Start the aircraft departure process
        yield self.env.process(
            self.simulate_aircraft_departure_process(aircraft=aircraft,
                                                    origin_vertiport_id=aircraft.origin_vertiport_id, 
                                                    destination_vertiport_id=destination_vertiport_id)
        )        

    def simulate_terminal_airspace_arrival_process(self, aircraft: object, arriving_passengers: list):
        holding_start = self.env.now
        
        # Increase aircraft arrival queue counter
        self.event_saver.update_aircraft_arrival_queue_counter(vertiport_id=aircraft.destination_vertiport_id,
                                                               queue_update=1)
        
        # Request arrival fix resource
        arrival_fix_usage_request, arrival_fix_resource = self.request_fix_resource(flight_direction=aircraft.flight_direction, operation_type='arrival')
        self.logger.debug(f'Aircraft {aircraft.tail_number} requesting arrival fix resource at {aircraft.destination_vertiport_id}.'
                         f' Number of holding aircraft queued at {aircraft.destination_vertiport_id}: {len(arrival_fix_resource.queue)}'
                         f' Number of available aircraft at {aircraft.destination_vertiport_id}: {self.check_num_available_aircraft(aircraft.destination_vertiport_id)}')
        # Trigger the stopping event
        self.stopping_events['aircraft_faf_arrival_event'].succeed()  

        # Wait until getting the arrival fix usage request
        yield arrival_fix_usage_request
        self.logger.debug(f'Aircraft {aircraft.tail_number} has been assigned to the arrival fix resource at {aircraft.destination_vertiport_id}')

        holding_end = self.env.now
        aircraft.holding_time = holding_end - holding_start
        aircraft.update_holding_energy_consumption(aircraft.holding_time)
        aircraft.save_process_time(event='holding', process_time=aircraft.holding_time)

        self.event_saver.save_aircraft_holding_time(vertiport_id=aircraft.destination_vertiport_id,
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
            # Save flight_direction
            flight_direction = aircraft.flight_direction
            # Landing process
            yield self.env.process(self.simulate_landing_process(aircraft=aircraft))
            # Taxi
            yield self.env.process(self.simulate_taxi_process(aircraft=aircraft, operation_type='arrival'))
            # Update number of aircraft status at the vertiports
            self.update_ground_aircraft_count(vertiport_id=aircraft.destination_vertiport_id, update=1)
            self.update_flying_aircraft_count(update=-1)
            self.save_passenger_trip_times(aircraft=aircraft, flight_direction=flight_direction)

            # Put aircraft into available aircraft store
            self.put_aircraft_into_available_aircraft_store(vertiport_id=aircraft.destination_vertiport_id,
                                                            aircraft=aircraft) 
            self.logger.debug(f'|{duplicate_str(aircraft.tail_number)}| Aircraft {aircraft.tail_number} is now ready for allocation.')
            aircraft.status = AircraftStatus.IDLE            
            # Trigger the stopping event
            self.stopping_events['aircraft_parking_pad_arrival_event'].succeed()

        # Only FATO case and starting point is not a FATO
        elif aircraft.parking_space_id is None and aircraft.assigned_fato_id is None:
            # NOTE: We don't request FATO here because it will be requested in the landing_process. However
            # in the case of single FATO, we are increasing the FATO reservation time from 
            # time_descend_transition + time_hover_descend to time_descend_transition + time_hover_descend + time_descend
            # yield self.env.process(self.fato_pad_request(aircraft=aircraft, operation_type='arrival'))  

            # Landing process
            yield self.env.process(self.simulate_landing_process(aircraft=aircraft)) 
            # Update number of aircraft status at the vertiports
            self.update_ground_aircraft_count(vertiport_id=aircraft.destination_vertiport_id, update=1)
            self.update_flying_aircraft_count(update=-1)   
            self.save_passenger_trip_times(aircraft=aircraft)
                   
            # Put aircraft into available aircraft store
            self.put_aircraft_into_available_aircraft_store(vertiport_id=aircraft.destination_vertiport_id,
                                                            aircraft=aircraft)   

            # Trigger the stopping event
            self.stopping_events['aircraft_parking_pad_arrival_event'].succeed()           

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
            # Update number of aircraft status at the vertiports
            self.update_ground_aircraft_count(vertiport_id=aircraft.destination_vertiport_id, update=1)

            self.logger.debug(f'Created: Aircraft {aircraft.tail_number} created at {aircraft.origin_vertiport_id} with SOC: {aircraft.soc}, location: {aircraft.location}')

            # Put aircraft into available aircraft store
            self.put_aircraft_into_available_aircraft_store(vertiport_id=aircraft.destination_vertiport_id,
                                                            aircraft=aircraft) 
            self.logger.debug(f'|{duplicate_str(aircraft.tail_number)}| Aircraft {aircraft.tail_number} is now ready for allocation.')         
            # Trigger the stopping event
            self.stopping_events['aircraft_parking_pad_arrival_event'].succeed() 
        
        # Only FATO case and the starting location is a FATO
        elif aircraft.assigned_fato_id is not None:
            # Update number of aircraft status at the vertiports
            self.update_ground_aircraft_count(vertiport_id=aircraft.destination_vertiport_id, update=1)

            self.logger.debug(f'Created: Aircraft {aircraft.tail_number} created at {aircraft.origin_vertiport_id} with SOC: {aircraft.soc}, location: {aircraft.location}')

            # Get FATO
            yield self.env.process(self.fato_pad_request(aircraft=aircraft, operation_type='arrival', fato_id=aircraft.assigned_fato_id))
            # Put aircraft into available aircraft store
            self.put_aircraft_into_available_aircraft_store(vertiport_id=aircraft.destination_vertiport_id,
                                                            aircraft=aircraft) 
            self.logger.debug(f'|{duplicate_str(aircraft.tail_number)}| Aircraft {aircraft.tail_number} is now ready for allocation.')
            aircraft.status = AircraftStatus.IDLE            
            # Trigger the stopping event
            self.stopping_events['aircraft_parking_pad_arrival_event'].succeed()         
            
        # If the aircraft is assigned to a parking pad
        elif aircraft.parking_space_id is not None:
            # Update number of aircraft status at the vertiports
            self.update_ground_aircraft_count(vertiport_id=aircraft.destination_vertiport_id, update=1)

            self.logger.debug(f'Created: Aircraft {aircraft.tail_number} created at {aircraft.origin_vertiport_id} with SOC: {aircraft.soc}, location: {aircraft.location}')

            # Get Parking pad
            yield self.env.process(self.parking_pad_request(aircraft=aircraft, parking_space_id=aircraft.parking_space_id))
            if aircraft.initial_process == AircraftStatus.CHARGE:
                # Charging process
                yield self.env.process(self.aircraft_charging_process(aircraft=aircraft))
            elif aircraft.initial_process == AircraftStatus.IDLE:
                # Put aircraft into available aircraft store
                self.put_aircraft_into_available_aircraft_store(vertiport_id=aircraft.destination_vertiport_id,
                                                                aircraft=aircraft)
                self.stopping_events['aircraft_parking_pad_arrival_event'].succeed()
            else:
                raise ValueError('Unknown initial process for the aircraft')        

    def aircraft_charging_process(self, aircraft: object):
        # TODO: Use a better design pattern for this
        if self.sim_params['step_by_step_sim'] == 'auto':
            # Charge the aircraft
            yield self.env.process(
                aircraft.charge_aircraft_rl()
            )
        else:
            # Charge the aircraft
            yield self.env.process(
                aircraft.charge_aircraft(
                    parking_space=aircraft.parking_space,
                    shared_charger=self.vertiports[aircraft.destination_vertiport_id].shared_charger_sets
                )
            )

        # Put aircraft into available aircraft store
        self.put_aircraft_into_available_aircraft_store(vertiport_id=aircraft.destination_vertiport_id,
                                                        aircraft=aircraft)

        if self.sim_params['only_aircraft_simulation'] and not self.sim_params['network_simulation']:
            yield self.env.process(
                self.simulate_aircraft_departure_process(aircraft=aircraft, origin_vertiport_id=aircraft.origin_vertiport_id, destination_vertiport_id=None)
            )     

# PASSENGER RELATED METHODS
# -------------------------
    def simulate_passenger_arrival(self, passenger):
        """ Simulate passenger."""
        # Save passenger creation time
        self.event_saver.save_agent_state(agent=passenger, agent_type='passenger', event='vertiport_entrance')
        passenger.vertiport_arrival_time = self.env.now

        # Put the passenger into the waiting room
        yield self.env.process(self.put_passenger_into_waiting_room(passenger))

    def put_passenger_into_waiting_room(self, passenger: object) -> None:
        """
        Puts the passenger into the waiting room based on their flight destination and triggers scheduler
        :param passenger:
        :return:
        """
        # Define the location of the passenger as the waiting room at their current location
        passenger.location = f'{passenger.origin_vertiport_id}_ROOM'
        # Save the current state of the passenger
        self.event_saver.save_agent_state(agent=passenger, agent_type='passenger', event='enter_waiting_room')
        # Record the current time as the passenger's waiting room arrival time
        passenger.waiting_room_arrival_time = self.env.now
        # Get the waiting room that corresponds to the passenger's destination
        passengers_waiting_room = self.vertiports[passenger.origin_vertiport_id].waiting_room_stores[passenger.destination_vertiport_id]
        # Put the passenger into the waiting room and keep a reference to it
        passengers_waiting_room.put(passenger)
        passenger.waiting_room_store = passengers_waiting_room
        # Log the passenger's arrival
        self.passenger_logger.debug(f'Passenger {passenger.passenger_id} entered the waiting room at {passenger.origin_vertiport_id}. Currently waiting passengers: {[p.passenger_id for p in passengers_waiting_room.items]}.')

        # Trigger the stopping event
        self.stopping_events['passenger_arrival_event'].succeed()


