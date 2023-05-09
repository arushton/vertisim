from typing import List, Dict
import simpy
from collections import defaultdict

class Airspace:
    def __init__(self, env: simpy.Environment(), vertiports: Dict, holding_unit_capacity: int = 100):
        self.env = env
        self.vertiports = vertiports
        self.holding_unit_capacity = holding_unit_capacity
        self.airlink_resources = self.create_airlink_resources()

    def create_airlink_resources(self, waypoint_ids):
        waypoint_resources = defaultdict(dict)
        for airlink_id, waypoint_id_list in waypoint_ids.items():
            for waypoint_id in waypoint_id_list.values():
                # The last one (holding unit) will have capacity of holding_unit_capacity
                if waypoint_id == waypoint_id_list[-1]:
                    waypoint_resources[airlink_id][waypoint_id] = simpy.Resource(self.env, capacity=self.holding_unit_capacity)
                else:
                    waypoint_resources[airlink_id][waypoint_id] = simpy.Resource(self.env, capacity=1)
        return waypoint_resources