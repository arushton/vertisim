import random
from utils.distribution_generator import DistributionGenerator
from typing import Dict, Union


class Passenger:
    """
    Passenger agent. If the constant is None, then the distributions from vertiport_manager will be used.
    Distributions are not inputted directly to the passenger, because it will increase the overhead of each passenger
    object.
    """

    def __init__(self, env, passenger_id,
                 dest_vertiport_id: int,
                 car_to_entrance_walking_time_constant: Union[float, None],
                 security_check_time_constant: Union[float, None],
                 waiting_room_to_boarding_gate_walking_time_constant: Union[float, None],
                 boarding_gate_to_aircraft_time_constant: Union[float, None],
                 embark_disembark_time_constant: Union[float, None],
                 deboard_aircraft_and_walk_to_exit_constant: Union[float, None],
                 randomize_constants: bool,
                 vertiport_manager: object):
        self.env = env
        self.passenger_id = passenger_id
        self.dest_vertiport_id = dest_vertiport_id
        self.car_to_entrance_walking_time_constant = car_to_entrance_walking_time_constant
        self.security_check_time_constant = security_check_time_constant
        self.waiting_room_to_boarding_gate_walking_time_constant = waiting_room_to_boarding_gate_walking_time_constant
        self.boarding_gate_to_aircraft_time_constant = boarding_gate_to_aircraft_time_constant
        self.embark_disembark_time_constant = embark_disembark_time_constant
        self.deboard_aircraft_and_walk_to_exit_constant = deboard_aircraft_and_walk_to_exit_constant
        self.randomize_constants = randomize_constants
        self.vertiport_manager = vertiport_manager
        self.vertiport_arrival_time = None
        self.waiting_room_arrival_time = None
        self.waiting_room_store = None

    def walk_to_entrance(self):
        """ From car to the exit gate."""
        if self.car_to_entrance_walking_time_constant is not None:
            if self.randomize_constants:
                yield self.env.timeout(random.randint(
                    max(0, round(
                        self.car_to_entrance_walking_time_constant - self.car_to_entrance_walking_time_constant / 2)),
                    round(self.car_to_entrance_walking_time_constant + self.car_to_entrance_walking_time_constant / 2)
                )
                )
            else:
                yield self.env.timeout(self.car_to_entrance_walking_time_constant)
        elif self.vertiport_manager.passenger_distributions['car_to_entrance_walking_time_dist']:
            dist = self.vertiport_manager.passenger_distributions['car_to_entrance_walking_time_dist']
            distribution = DistributionGenerator(
                distribution_params=dist,
                max_val_in_dist=dist['max_val_in_dist'])
            yield self.env.timeout(distribution.pick_number_from_distribution())
        else:
            raise ValueError("No walking time distribution or constant defined.")

    def security_check(self):
        """ Security check."""
        if self.security_check_time_constant is not None:
            if self.randomize_constants:
                yield self.env.timeout(random.randint(
                    max(0, round(self.security_check_time_constant - self.security_check_time_constant / 2)),
                    round(self.security_check_time_constant + self.security_check_time_constant / 2)
                )
                )
            else:
                yield self.env.timeout(self.security_check_time_constant)
        elif self.vertiport_manager.passenger_distributions['security_check_time_dist']:
            dist = self.vertiport_manager.passenger_distributions['security_check_time_dist']
            distribution = DistributionGenerator(distribution_params=dist,
                                                 max_val_in_dist=dist['max_val_in_dist'])
            yield self.env.timeout(distribution.pick_number_from_distribution())
        else:
            raise ValueError("No security check time distribution or constant defined.")

    def waiting_room_to_boarding_gate(self):
        """ From waiting room to boarding gate."""
        if self.waiting_room_to_boarding_gate_walking_time_constant is not None:
            if self.randomize_constants:
                yield self.env.timeout(random.randint(
                    max(0, round(
                        self.waiting_room_to_boarding_gate_walking_time_constant - self.waiting_room_to_boarding_gate_walking_time_constant / 2)),
                    round(
                        self.waiting_room_to_boarding_gate_walking_time_constant + self.waiting_room_to_boarding_gate_walking_time_constant / 2)
                )
                )
            else:
                yield self.env.timeout(self.waiting_room_to_boarding_gate_walking_time_constant)
        elif self.vertiport_manager.passenger_distributions['waiting_room_to_boarding_gate_walking_time_dist']:
            dist = self.vertiport_manager.passenger_distributions['waiting_room_to_boarding_gate_walking_time_dist']
            distribution = DistributionGenerator(
                distribution_params=dist,
                max_val_in_dist=dist['max_val_in_dist'])
            yield self.env.timeout(distribution.pick_number_from_distribution())
        else:
            raise ValueError("No waiting room to boarding gate walking time distribution or constant defined.")

    def boarding_gate_to_aircraft(self):
        """ From boarding gate to aircraft."""
        if self.boarding_gate_to_aircraft_time_constant is not None:
            if self.randomize_constants:
                yield self.env.timeout(random.randint(
                    max(0, round(
                        self.boarding_gate_to_aircraft_time_constant - self.boarding_gate_to_aircraft_time_constant / 2)),
                    round(
                        self.boarding_gate_to_aircraft_time_constant + self.boarding_gate_to_aircraft_time_constant / 2)
                )
                )
            else:
                yield self.env.timeout(self.boarding_gate_to_aircraft_time_constant)
        elif self.vertiport_manager.passenger_distributions['boarding_gate_to_aircraft_time_dist']:
            dist = self.vertiport_manager.passenger_distributions['boarding_gate_to_aircraft_time_dist']
            distribution = DistributionGenerator(
                distribution_params=dist,
                max_val_in_dist=dist['max_val_in_dist'])
            yield self.env.timeout(distribution.pick_number_from_distribution())
        else:
            raise ValueError("No boarding gate to aircraft time distribution or constant defined.")

    # THIS SHOULD BE IN VERTIPORT MANAGER
    # def simulate_passenger(self):
    #     """ Simulate passenger."""
    #     self.event_saver.save_agent_creation_time(agent_id=self.passenger_id,
    #                                               agent_type='passenger')
    #
    #     # Simulate agent's walk from car to the vertiport entrance
    #     yield self.env.process(self.walk_to_entrance())
    #     # Save the time when the passenger arrives at the vertiport entrance
    #     self.event_saver.save_passenger_vertiport_entrance_arrival_time(agent_id=self.passenger_id)
    #     # Simulate agent's security check
    #     yield self.env.process(self.security_check())
    #     # Save the time when the passenger finishes the security check
    #     self.event_saver.save_passenger_security_check_time(agent_id=self.passenger_id)

        # Passenger enters the waiting room based on their flight destination

    # OLD CODE
        # # Puts agent to a waiting room wrt their destination.
        # currentWaitingRoom = self.vertiport.WAITINGROOMdic[
        #     list(self.vertiport.WAITINGROOMdic)[departingAgent.agentFlightDirection]]
        # yield currentWaitingRoom.put(departingAgent.agentID)
        #
        # # Check if there are any eligible flights.
        # yield self.env.process(FlightGeneration(self.env, maxWaitingTime, aircraftCapacity,
        #                                         self.vertiport).checkWaitingRoom(currentWaitingRoom))
