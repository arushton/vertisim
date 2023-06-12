from typing import List, Dict
import simpy
from utils.distance import haversine_dist
from collections import defaultdict
import pandas as pd

class Airspace:
    def __init__(self, env: simpy.Environment(), 
                 holding_unit_capacity: int = 10,
                 airlink_capacity: int = 1,
                 airlink_segment_length_miles: float = 0.25,
                 waypoint_ids: Dict = None,
                 waypoint_locations: Dict = None,
                 flight_directions: List = None):
        self.env = env
        self.holding_unit_capacity = holding_unit_capacity
        self.airlink_capacity = airlink_capacity
        self.airlink_segment_length_miles = airlink_segment_length_miles
        self.waypoint_ids = waypoint_ids
        self.flight_directions = list(waypoint_ids.keys())
        self.waypoint_locations = waypoint_locations
        self.flight_directions = flight_directions
        self.waypoint_distances = Airspace.compute_distances_bw_waypoints(waypoint_locations)
        self.airlink_resources = self.create_airlink_resources()
        self.airspace_resource_states = self.get_airspace_states()

    def create_airlink_resources(self):
        airlink_resources = defaultdict(dict)
        for flight_direction, waypoint_id_list in self.waypoint_ids.items():
            # origin = flight_direction.split('_')[0]
            # destination = flight_direction.split('_')[1]
            for waypoint_id in waypoint_id_list:
                # The second to last one (holding unit -approach departure fixes) will have capacity of holding_unit_capacity
                # Departure fix
                if waypoint_id in [waypoint_id_list[0], waypoint_id_list[1], waypoint_id_list[-1], waypoint_id_list[-2]]:
                    airlink_resources[flight_direction][waypoint_id] = simpy.Resource(self.env, capacity=1) # Overtake is not allowed
                elif waypoint_id == waypoint_id_list[-3]:
                    airlink_resources[flight_direction][waypoint_id] = simpy.Resource(self.env, capacity=self.holding_unit_capacity)
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
    
    @staticmethod
    def calculate_distance(row1, row2, unit='meter'):
        return haversine_dist(row1['latitude'], row1['longitude'], 
                            row2['latitude'], row2['longitude'], 
                            unit=unit)

    @staticmethod
    def calculate_and_store_distances(df):
        distances = defaultdict(dict)
        for (_, row1), (_, row2) in zip(df.iterrows(), df.iloc[1:].iterrows()):
            distance = Airspace.calculate_distance(row1, row2)
            distances[row1['waypoint_id']][row2['waypoint_id']] = distance
            distances[row2['waypoint_id']][row1['waypoint_id']] = distance
        return distances


    @staticmethod
    def calculate_first_last_distance(df, distances):
        first_row = df.iloc[0]
        last_row = df.iloc[-1]
        distance = Airspace.calculate_distance(first_row, last_row)
        distances[first_row['waypoint_id']][last_row['waypoint_id']] = distance
        distances[last_row['waypoint_id']][first_row['waypoint_id']] = distance
        return distances


    @staticmethod
    def compute_distances_bw_waypoints(df):
        # Check if input is a dictionary and convert to DataFrame if necessary
        if isinstance(df, dict):
            df = pd.DataFrame.from_dict(df, orient='index', columns=['latitude', 'longitude', 'altitude'])
            df.index.set_names(['waypoint_id'], inplace=True)
            df.reset_index(inplace=True)                
        distances = Airspace.calculate_and_store_distances(df)
        distances = Airspace.calculate_first_last_distance(df, distances)
        return distances