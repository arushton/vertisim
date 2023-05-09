import pandas as pd
from utils.haversine import haversine_dist
from utils.read_files import read_input_file

def calc_vertiport_distances(vertiport_network_file_path: str) -> pd.DataFrame:
    # Calculates the distance between origin vertiport and destination vertiports and creates a dictionary of distances
    # for each origin vertiport. key should be vertiport_id and value should be haversine distance. Unit is miles/km.
    vertiport_network = read_input_file(vertiport_network_file_path)
    vertiport_network['distance_miles'] = vertiport_network.apply(
        lambda row: haversine_dist(row['o_vert_lat'], row['o_vert_lon'], row['d_vert_lat'], row['d_vert_lon']), axis=1)
    return vertiport_network