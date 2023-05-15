from typing import List, Dict
import simpy
from collections import defaultdict

class Airspace:
    def __init__(self, env: simpy.Environment(), 
                 vertiports: Dict = None,
                 airlink_capacity: int = 1,
                 airlink_segment_length_miles: float = 0.25,
                 waypoint_ids: Dict = None,
                 waypoint_locations: Dict = None):
        self.env = env
        self.vertiports = vertiports
        self.airlink_capacity = airlink_capacity
        self.airlink_segment_length_miles = airlink_segment_length_miles
        self.waypoint_ids = waypoint_ids
        self.flight_directions = list(waypoint_ids.keys())
        self.waypoint_locations = waypoint_locations
        self.airlink_resources = self.create_airlink_resources()
        self.airspace_resource_states = self.get_airspace_states()

    def create_airlink_resources(self):
        airlink_resources = defaultdict(dict)
        for flight_direction, waypoint_id_list in self.waypoint_ids.items():
            origin = flight_direction.split('_')[0]
            destination = flight_direction.split('_')[1]
            for waypoint_id in waypoint_id_list:
                # The last one (holding unit -approach departure fixes) will have capacity of holding_unit_capacity
                if waypoint_id == waypoint_id_list[0]:
                    airlink_resources[flight_direction][waypoint_id] = self.vertiports[origin].departure_fix_resource
                elif waypoint_id == waypoint_id_list[-1]:
                    airlink_resources[flight_direction][waypoint_id] = self.vertiports[destination].arrival_fix_resource
                else:
                    airlink_resources[flight_direction][waypoint_id] = simpy.Resource(self.env, capacity=self.airlink_capacity)
        return airlink_resources
    
    def get_airspace_states(self):
        return {
            flight_direction: {
                waypoint_id: {
                    # 'waypoint_resource': airlink_resource,
                    'num_jobs_in_service': airlink_resource.count,
                    'num_jobs_in_queue': len(airlink_resource.queue)
                }
                for waypoint_id, airlink_resource in airlink_resources.items()
            }
            for flight_direction, airlink_resources in self.airlink_resources.items()
        }
