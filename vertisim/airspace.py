from typing import List, Dict
import simpy
from collections import defaultdict

class Airspace:
    def __init__(self, env: simpy.Environment(), 
                 holding_unit_capacity: int = 100, 
                 airlink_capacity: int = 1,
                 airlink_segment_length_miles: float = 0.25,
                 waypoint_ids: Dict = None,
                 waypoint_locations: Dict = None):
        self.env = env
        self.holding_unit_capacity = holding_unit_capacity
        self.airlink_capacity = airlink_capacity
        self.airlink_segment_length_miles = airlink_segment_length_miles
        self.waypoint_ids = waypoint_ids
        self.waypoint_locations = waypoint_locations
        self.airlink_resources = self.create_airlink_resources()

    def create_airlink_resources(self):
        airlink_resources = defaultdict(dict)
        for flight_direction, waypoint_id_list in self.waypoint_ids.items():
            for waypoint_id in waypoint_id_list:
                # The last one (holding unit) will have capacity of holding_unit_capacity
                if waypoint_id == waypoint_id_list[-1]:
                    airlink_resources[flight_direction][waypoint_id] = simpy.Resource(self.env, capacity=self.holding_unit_capacity)
                else:
                    airlink_resources[flight_direction][waypoint_id] = simpy.Resource(self.env, capacity=self.airlink_capacity)
        return airlink_resources