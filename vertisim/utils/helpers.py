import random
import numpy as np
from utils.units import sec_to_ms
from typing import List, Union, Dict, Any
import re
import pandas as pd # For type hinting


def set_seed(seed=None):
    """
    Sets the seed for random number generation.
    :param seed: an optional seed value (int)
    :return: None
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    else:
        random.seed(42)
        np.random.seed(42)


def compute_interarrival_times_from_schedule(schedule):
    """
    Computes interarrival times from a schedule.
    :param schedule:
    :return:
    """
    return np.diff(schedule, prepend=0)


def cumulative_sum_array(array: Union[np.ndarray, List]) -> np.ndarray:
    """
    Cumulative sum of an array.
    :param array:
    :return: np.ndarray
    """
    return np.cumsum(array)


def flatten(t):
    """
    Flatten a nested list structure.
    :param t:
    :return:
    """
    return [item for sublist in t for item in sublist]


def get_key_from_value(dictionary, search_val):
    """
    Get key from value in a dictionary.
    :param dictionary:
    :param search_val:
    :return:
    """
    return [key for key, value in dictionary.items() if search_val == value][0]


def get_key(my_dict, key):
    """
    Function that returns None if the key is not found, if found return value
    :param my_dict:
    :param key:
    :return:
    """
    return my_dict[key] if key in my_dict else None


def none_checker(val):
    """
    Checks if a value is None. If None returns None, else returns the value.
    :param val:
    :return:
    """
    return None if val is None else val


def timestamp_to_datetime(sim_start_time, sim_time):
    """
    Converts a timestamp to a datetime.
    :param sim_start_time:
    :param sim_time:
    :return:
    """
    # date_time = datetime.fromtimestamp(current_timestamp)
    # return date_time.strftime('%Y:%m:%d:%H:%M:%S.%f')
    return sim_start_time + sim_time


def create_num_charger_list(layouts_list, shared_charger_sets):
    """
    Create a list of number of chargers for each layout
    :param layouts_list:
    :param shared_charger_sets:
    :return:
    """
    return [len(shared_charger_sets) for _ in layouts_list]


def is_shared_charger(shared_charger_sets) -> bool:
    """
    Check if the vertiport has shared chargers
    :param shared_charger_sets:
    :return:
    """
    return shared_charger_sets is not None


def check_if_dataframe_is_empty(df):
    """
    Check if a dataframe is empty.
    :param df:
    :return:
    """
    return df.empty


def map_nested_dict_keys_to_values_from_list(dictionary, list_of_keys, last_key):
    """
    Map nested dictionary keys to values from a list input.
    :param dictionary:
    :param list_of_keys:
    :param last_key:
    :return:
    """
    return [dictionary[key][last_key] for key in list_of_keys]


def nested_dict_all_values(d, depth):
    """
    Usage:
        list(nested_dict_values({1: {2: 3, 4: 5}}, 2))
        list(nested_dict_values(vertipad_PARK,2))
    """
    if depth == 1:
        for i in d.values():
            yield i
    else:
        for v in d.values():
            if isinstance(v, dict):
                for i in nested_dict_all_values(v, depth - 1):
                    yield i


def nested_dict_all_keys(d, depth):
    """
    Usage:
        list(nested_dict_keys({1: {2: 3, 4: 5}}, 2))
        list(nested_dict_keys(vertipad_PARK,2))
    """
    if depth == 1:
        for i in d.keys():
            yield i
    else:
        for v in d.values():
            if isinstance(v, dict):
                for i in nested_dict_all_keys(v, depth - 1):
                    yield i


def nested_dict_filter_keys(d, depth, key):
    """
    Usage:
        list(nested_dict_keys({1: {2: 3, 4: 5}}, 2))
        list(nested_dict_keys(vertipad_PARK,2))
    """
    if depth == 1:
        for i in d.keys():
            if i == key:
                yield d[key]
    else:
        for v in d.values():
            if isinstance(v, dict):
                for i in nested_dict_filter_keys(v, depth - 1, key):
                    yield i


def get_str_before_first_occurrence_of_char(string, char):
    """
    Get string before first occurrence of a character.
    :param string:
    :param char:
    :return:
    """
    return string.split(char)[0]


def get_passenger_ids_from_passenger_list(passenger_list):
    """
    Get passenger ids from a passenger list.
    :param passenger_list:
    :return:
    """
    return [passenger.passenger_id for passenger in passenger_list]

def get_passenger_id_str_from_passenger_list(passenger_list):
    """
    Get passenger ids from a passenger list.
    :param passenger_list:
    :return:
    """
    return [f'passenger_{passenger.passenger_id}' for passenger in passenger_list]


def calculate_passenger_consolidation_time(departing_passengers):
    """
    Find the consolidation time by substracting the waiting room arrival time of the last passenger from the first passenger
    """
    return departing_passengers[-1].waiting_room_arrival_time - departing_passengers[0].waiting_room_arrival_time


def remove_larger_keys(dic1, dic2):
    # Deletes all the keys in dic1 that are greater than the highest key of dic2
    for key in list(dic1.keys()):
        if key > max(list(dic2.keys())):
            del dic1[key]
    return dic1
    

def get_values_from_nested_dict(dictionary, key):
    """
    Get values from a nested dictionary given second level key.
    :param dictionary:
    :param key:
    :return:
    """
    return [v[key] for v in dictionary.values()]


def get_length_of_longest_list(lst):
    return len(max(lst, key=len))


def get_length_of_shortest_list(lst):
    return len(min(lst, key=len))


def is_sqlite3(filename):
    from os.path import isfile, getsize

    if not isfile(filename):
        return False
    if getsize(filename) < 100: # SQLite database file header is 100 bytes
        return False

    with open(filename, 'rb') as fd:
        header = fd.read(100)

    return header[:16] == "SQLite format 3\x00"


def find_first_int(string):
    """
    Find the first integer in a string.
    """
    return int(re.findall(r'\d+', string)[0])


def find_second_int(string):
    """
    Find the second integer in a string.
    """
    return int(re.findall(r'\d+', string)[1])


def get_all_aircraft_models(network_and_demand: dict) -> set:
    return list(set(
        model 
        for vertiport_data in network_and_demand['vertiports'].values()
            for model in vertiport_data['aircraft_arrival_process']
            ['aircraft_fleet_specs'].keys()
            ))


def get_dict_vals_as_list(llist, key) -> List:
    """
    Returns a list of values from a list of dictionaries given a key.

    :param llist:
    :param key:
    """
    return [d[key] for d in llist]


def check_whether_node_exists(node_dict: Dict, node_id: Any):
    """
    Check whether a node exists in a dictionary of nodes.

    :param node_dict:
    :param node_id:
    """
    return node_id in node_dict.keys()


def check_if_none_exists(column: pd.Series) -> bool:
    """
    Check whether a column in a dataframe contains None values.

    :param df:
    :param column_name:
    """
    return column.isnull().values.any()


def check_if_all_none(column: pd.Series) -> bool:
    """
    Check whether a column in a dataframe contains only None values.

    :param df:
    :param column_name:
    """
    return column.isnull().values.all()

def convert_to_list(x: Any):
    """
    Convert an object to a list.
    """
    if isinstance(x, list):
        return x
    elif isinstance(x, tuple):
        return list(x)
    elif isinstance(x, np.ndarray):
        return x.tolist()
    elif isinstance(x, str):
        return [x]
    else:
        raise TypeError(
            f'Object is not a list, tuple or numpy array. The object is of type: {type(x)}. It is not supported.'
        )


def careful_round(value, decimal_places=2):
    """
    Round a value to 2 decimal places.
    """
    return None if value is None else round(value, decimal_places)

def careful_conversion(value):
    """
    Convert a value to float if it is not None.
    """
    if value is None:
        return None
    elif isinstance(value, str):
        return float(value)
    else:
        return value


def create_dict_for_fixes(airspace_nodes: Dict) -> Dict:
    """
    Create a dictionary for fixes.
    """
    fix_nodes = {'approach_fix_node': [], 'departure_fix_node': []}
    for key, value_list in airspace_nodes.items():
        for value in value_list:
            if 'approach' in value.lower():
                fix_nodes['approach_fix_node'].append(value)
            elif 'departure' in value.lower():
                fix_nodes['departure_fix_node'].append(value)
    return fix_nodes


def check_not_none(value):
    """
    Check whether a value is None.
    """
    return value is not None

def create_save_path(original_path, list_of_keys):
    # Extract the directory from the original path
    directory = '/'.join(original_path.split('/')[:-1])

    # Create the new filename using the keys from the dictionary
    new_filename = f"network_{'_'.join(list_of_keys)}.csv"

    # Create the new path by joining the directory and the new filename
    return f"{directory}/{new_filename}"

def check_magnitude_order(value1, value2):
    """
    Check whether the magnitude of value1 is greater than the magnitude of value2.
    """
    if value1 > value2:
        raise ValueError(
            f'The magnitude of value1 ({value1}) is greater than the magnitude of value2 ({value2}).'
        )
    


# def nested_dict_filter_values(d, depth, value):
#     """
#     Usage:
#         list(nested_dict_values({1: {2: 3, 4: 5}}, 2))
#         list(nested_dict_values(vertipad_PARK,2))
#     """
#     if depth == 1:
#         for i in d.values():
#             if d[i] == value:
#                 yield i
#
#     else:
#         for v in d.values():
#             if isinstance(v, dict):
#                 for i in nested_dict_filter_values(v, depth - 1, value):
#                     yield i

# def inverse_cumcum(cumsum_array: np.ndarray) -> np.ndarray:
#     """
#     Inverse of cumulative sum array.
#     :param cumsum_array:
#     :return:
#     """
#     return np.diff(cumsum_array, prepend=0)
