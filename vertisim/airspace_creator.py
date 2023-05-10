from utils.haversine import haversine_dist
import numpy as np
from typing import List, Dict
from collections import defaultdict
import pandas as pd # For type hinting

class AirspaceCreator:
    def __init__(self, vertiports: Dict, airlink_segment_length_miles: float = 0.25, vertiport_distances: pd.DataFrame = None):
        self.vertiports = vertiports
        self.airlink_segment_length_miles = airlink_segment_length_miles
        self.vertiport_distances = vertiport_distances
        self.num_waypoints_per_airlink = self.determine_num_waypoints()
        self.airlink_start_end_points = self.get_airlink_start_end_points()
        self.waypoint_ids = self.create_waypoint_ids()
        self.waypoints = self.create_waypoints()
        self.waypoint_locations = self.match_waypoint_names_locations()


    @staticmethod
    def generate_waypoints(lat1, lon1, lat2, lon2, num_waypoints):
        # Calculate haversine distance between the two points
        distance_miles = haversine_dist(lat1, lon1, lat2, lon2, unit='mile')

        # Convert distance to radians
        c = distance_miles / 3958

        # Convert latitude and longitude to radians
        lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
        lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
        
        waypoints = []
        for i in range(1, num_waypoints + 1):
            f = i / (num_waypoints + 1)
            A = np.sin((1 - f) * c) / np.sin(c)
            B = np.sin(f * c) / np.sin(c)
            x = A * np.cos(lat1_rad) * np.cos(lon1_rad) + B * np.cos(lat2_rad) * np.cos(lon2_rad)
            y = A * np.cos(lat1_rad) * np.sin(lon1_rad) + B * np.cos(lat2_rad) * np.sin(lon2_rad)
            z = A * np.sin(lat1_rad) + B * np.sin(lat2_rad)
            lat_rad = np.arctan2(z, np.sqrt(x ** 2 + y ** 2))
            lon_rad = np.arctan2(y, x)
            lat, lon = np.degrees(lat_rad), np.degrees(lon_rad)
            waypoints.append((lat, lon))
        # links = [(waypoints[i], waypoints[i + 1]) for i in range(len(waypoints) - 1)]
        return waypoints

    
    def determine_num_waypoints(self) -> Dict: # vertiport_distances: pd.DataFrame
        """
        Computes the required number of waypoints for each airlink in the vertiport_distances DataFrame.
        """
        num_waypoints_per_airlink = defaultdict(dict)
        for _, row in self.vertiport_distances.iterrows():
            origin_terminal_airspace_radius = self.vertiports[row['origin_vertiport_id']].vertiport_layout.terminal_airspace_radius
            destination_terminal_airspace_radius = self.vertiports[row['destination_vertiport_id']].vertiport_layout.terminal_airspace_radius
            airlink_length = row['distance_miles'] - origin_terminal_airspace_radius - destination_terminal_airspace_radius
            num_waypoints = round(airlink_length / self.airlink_segment_length_miles)
            num_waypoints_per_airlink[row['origin_vertiport_id'] + '_' + row['destination_vertiport_id']] = num_waypoints
        return num_waypoints_per_airlink

    def get_airlink_start_end_points(self):
        airlinks_start_end_endpoints = defaultdict(dict)
        for _, row in self.vertiport_distances.iterrows():
            origin_departure_fix_lat = self.vertiports[row['origin_vertiport_id']].vertiport_layout.departure_fix_lat_lng['departure_fix_lat'].iloc[0]
            origin_departure_fix_lng = self.vertiports[row['origin_vertiport_id']].vertiport_layout.departure_fix_lat_lng['departure_fix_lng'].iloc[0]
            dest_arrival_fix_lat = self.vertiports[row['destination_vertiport_id']].vertiport_layout.arrival_fix_lat_lng['arrival_fix_lat'].iloc[0]
            dest_arrival_fix_lng = self.vertiports[row['destination_vertiport_id']].vertiport_layout.arrival_fix_lat_lng['arrival_fix_lng'].iloc[0]
            airlinks_start_end_endpoints[row['origin_vertiport_id'] + '_' + row['destination_vertiport_id']] = (origin_departure_fix_lat, 
                                                                                                                origin_departure_fix_lng, 
                                                                                                                dest_arrival_fix_lat, 
                                                                                                                dest_arrival_fix_lng)
        return airlinks_start_end_endpoints


    def create_waypoint_ids(self):
        waypoint_ids = defaultdict(list)
        for flight_direction, num_waypoints in self.num_waypoints_per_airlink.items():
            for i in range(num_waypoints):
                if i == num_waypoints-1:
                    waypoint_ids[flight_direction].append(f'holding_unit_{flight_direction}')
                else:
                    waypoint_ids[flight_direction].append(f'{flight_direction}_{str(i)}')
        return waypoint_ids


    def create_waypoints(self):
        waypoints = defaultdict(list)
        for flight_direction, start_end_points in self.airlinks_start_endpoints.items():
            origin_departure_fix_lat, origin_departure_fix_lng, dest_arrival_fix_lat, dest_arrival_fix_lng = start_end_points
            num_waypoints = len(self.waypoint_ids[flight_direction])
            waypoints[flight_direction] = AirspaceCreator.generate_waypoints(origin_departure_fix_lat, 
                                                                            origin_departure_fix_lng, 
                                                                            dest_arrival_fix_lat, 
                                                                            dest_arrival_fix_lng, 
                                                                            num_waypoints)
        return waypoints

    def match_waypoint_names_locations(self):
        waypoint_locations = defaultdict(dict)
        for flight_direction, waypoint_id_list in self.waypoint_ids.items():
            for i, waypoint_id in enumerate(waypoint_id_list):
                waypoint_locations[waypoint_id] = self.waypoints[flight_direction][i]
        return waypoint_locations