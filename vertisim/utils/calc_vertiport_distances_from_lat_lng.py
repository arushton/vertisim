import pandas as pd
from utils.distance import haversine_dist
from utils.read_files import read_input_file
from utils.create_vertiport_network import create_fully_connected_vertiport_network
from utils.helpers import create_save_path
from typing import List, Dict

def calc_vertiport_distances(vertiport_network_file_path: str, 
                             vertiport_ids: List,
                             vertiport_layouts: Dict,
                             network_simulation: bool) -> pd.DataFrame:
    # Calculates the distance between origin vertiport and destination vertiports and creates a dictionary of distances
    # for each origin vertiport. key should be vertiport_id and value should be haversine distance. Unit is miles or km.
    vertiport_network = read_input_file(vertiport_network_file_path)
    # Check if vertiport network file has all vertiport ids
    if not set(vertiport_ids).issubset(set(vertiport_network['origin_vertiport_id'])):
        fato_coords_list = [
            (
                vertiport_layouts[vertiport_id]
                .fato_lat_lngs['fato_lat']
                .values[0],
                vertiport_layouts[vertiport_id]
                .fato_lat_lngs['fato_lon']
                .values[0],
            )
            for vertiport_id in vertiport_ids
        ]
        # Create a save path for the vertiport network file using the vertiport ids
        save_path = create_save_path(original_path=vertiport_network_file_path,
                                     list_of_keys=vertiport_ids)

        vertiport_network = create_fully_connected_vertiport_network(fato_coordinates=fato_coords_list,
                                                                     vertiport_ids=vertiport_ids,
                                                                     save_path=save_path,
                                                                     network_simulation=network_simulation)
        print('Vertiport network file has been recreated.')
    vertiport_network['distance_miles'] = vertiport_network.apply(
        lambda row: haversine_dist(row['o_vert_lat'], row['o_vert_lon'], row['d_vert_lat'], row['d_vert_lon']), axis=1)
    return vertiport_network