import numpy as np


def sec_to_ms(sec):
    if type(sec) not in [int, float, np.float64, np.float32, np.int_, np.array]:
        raise TypeError("Can't convert sec to ms. Duration (sec) format is not correct")
    else:
        return sec * 1000


def min_to_sec(min):
    if type(min) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError("Can't convert min to sec. Duration (min) format is not correct")
    else:
        return min * 60
