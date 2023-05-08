import random
from typing import List, Any

def weighted_random_choose(elements_list: List,
                           probabilities: List,
                           num_selection: int) -> List:
    
    # Create a new list with the desired probabilities for each element
    return [random.choices(elements_list, weights=probabilities)[0] for _ in range(num_selection)]

def random_choose_exclude_element(elements_list: List,
                                  exclude_element: Any,
                                  num_selection: int) -> List:
    # Choose num_selection elements from elements_list, excluding exclude_element
    return [random.choice([elem for elem in elements_list if elem != exclude_element]) for _ in range(num_selection)]
