from utils.haversine import haversine_dist
import numpy as np
from typing import List, Dict
from collections import defaultdict

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
    
    links = [(waypoints[i], waypoints[i + 1]) for i in range(len(waypoints) - 1)]
    
    return waypoints, links

def determine_num_waypoints(vertiports: Dict, airlink_segment_length_miles: float, vertiport_distances) -> Dict: # vertiport_distances: pd.DataFrame
    """
    Computes the required number of waypoints for each airlink in the vertiport_distances DataFrame.
    """
    num_waypoints_per_vertiport = defaultdict(dict)
    for _, row in vertiport_distances.iterrows():
        origin_terminal_airspace_radius = vertiports[row['origin_vertiport_id']].vertiport_layout.terminal_airspace_radius
        destination_terminal_airspace_radius = vertiports[row['destination_vertiport_id']].vertiport_layout.terminal_airspace_radius
        airlink_length = row['distance_miles'] - origin_terminal_airspace_radius - destination_terminal_airspace_radius
        num_waypoints = round(airlink_length / airlink_segment_length_miles)
        num_waypoints_per_vertiport[row['origin_vertiport_id'] + '_' + row['destination_vertiport_id']] = num_waypoints
    return num_waypoints_per_vertiport

def create_waypoint_ids(num_waypoints_per_vertiport):
    waypoint_ids = defaultdict(dict)
    for airlink_id, num_waypoints in num_waypoints_per_vertiport.items():
        for i in range(num_waypoints):
            if i == num_waypoints-1:
                waypoint_ids[airlink_id][i] = f'holding_unit_{airlink_id}'
            else:
                waypoint_ids[airlink_id][i] = f'waypoint_{airlink_id}_{i}'
    return waypoint_ids