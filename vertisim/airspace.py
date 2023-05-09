from typing import List, Dict
import simpy
from collections import defaultdict

class Airspace:
    def __init__(self, env: simpy.Environment(), waypoints: Dict):
        self.env = env
        self.waypoints = waypoints

    def create_waypoint_resources(self) -> Dict:
        waypoint_resources = defaultdict(dict)
        for direction, waypoint_list in self.waypoints.items():
            waypoint_resources[direction] = [simpy.Resource(self.env, capacity=1) for _ in range(len(waypoint_list))]
        return waypoint_resources
