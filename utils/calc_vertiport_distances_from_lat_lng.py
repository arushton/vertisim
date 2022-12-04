import numpy as np
from math import sin, cos, sqrt, atan2, radians
from typing import Dict
from utils.read_files import read_input_file


def calc_haversine_dist(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # 6367 for distance in KM for miles use 3958
    r = 3958

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return round(r * c)


def calc_destination_vertiport_distances(vertiport_network_file_path: str) -> Dict:
    # Calculate the distance between origin vertiport and destination vertiports and create a dictionary of distances
    # for each origin vertiport. key should be vertiport_id and value should be haversine distance. Unit is miles/km.
    vertiport_network = read_input_file(vertiport_network_file_path)
    vertiport_distances = {}
    for _, row in vertiport_network.iterrows():
        vertiport_distances[row['vertiport_id']] = calc_haversine_dist(row['o_vert_lat'],
                                                                       row['o_vert_lon'],
                                                                       row['d_vert_lat'],
                                                                       row['d_vert_lon'])
    return vertiport_distances

