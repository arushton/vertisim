from typing import Dict
from ..utils.units import miles_to_m


def time_to_arrival_estimator(cruise_speed: Dict, 
                              current_waypoint_id: str, 
                              origin_vertiport_id: str,
                              destination_vertiport_id: str,
                              flight_direction: str,
                              system_manager: object) -> float:
    """
    Estimates the time to arrival at the destination vertiport.
    """
    if destination_vertiport_id is None:
        return 0
    if origin_vertiport_id == destination_vertiport_id:
        return 0
    average_flight_time = system_manager.get_average_flight_time(flight_direction)
    initialization_checker = average_flight_time is None

    # If average flight time is not set, compute and update it.
    if average_flight_time is None:
        average_flight_time = system_manager.initial_flight_duration_estimate(origin_vertiport_id, destination_vertiport_id, cruise_speed)
        system_manager.set_average_flight_time(flight_direction, average_flight_time)
        system_manager.increase_flight_count(flight_direction)

    waypoint_rank = system_manager.airspace.get_waypoint_rank(current_waypoint_id, flight_direction)
    flight_length = system_manager.airspace.get_flight_length(flight_direction)

    # Calculate estimated time to arrival.
    estimated_time_to_arrival = average_flight_time * (flight_length - waypoint_rank) / flight_length

    # Reset average flight time to None if it was originally None.
    if initialization_checker:
        system_manager.set_average_flight_time(flight_direction, None)
        system_manager.decrease_flight_count(flight_direction)

    return estimated_time_to_arrival
