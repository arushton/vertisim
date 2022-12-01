import scipy.stats as stats
import numpy as np
from typing import Dict, Union
from utils.units import min_to_sec, sec_to_ms
import random


def pick_number(population, probabilities):
    """
    Picks a number from a distribution given population and probabilities.
    :param population: np.ndarray of values in the distribution
    :param probabilities: np.ndarray of probabilities of values in the distribution
    :return:
    """
    time = random.choices(population, probabilities)[0]
    time_sec = round(max(0, time))
    return sec_to_ms(time_sec)


class DistributionGenerator:
    def __init__(self, distribution_params: Dict, max_val_in_dist: Union[float, int]):
        self.distribution_params = distribution_params
        self.max_val_in_dist = max_val_in_dist
        self.population, self.probabilities = self.generate_distribution()

    def generate_distribution(self) -> [np.ndarray, np.ndarray]:
        """
        Generates a distribution given distribution name and parameters.
        :param distribution_params
        :param max_val_in_dist
        :return:
        population: np.ndarray of values in the distribution
        probabilities: np.ndarray of probabilities of values in the distribution
        """
        dist = getattr(stats, self.distribution_params['distribution_name'])
        population = np.linspace(0, self.max_val_in_dist, 1000)
        probabilities = dist.pdf(x=population, **self.distribution_params['parameters'])
        return population, probabilities

    def pick_number_from_distribution(self):
        """
        Picks a number from the distribution.
        :return:
        """
        return pick_number(self.population, self.probabilities)
