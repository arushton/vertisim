import numpy as np


def sec_to_ms(sec):
    if sec is None:
        return None
    elif type(sec) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError("Can't convert sec to ms. Duration (sec) format is not correct")
    else:
        return sec * 1000


def min_to_sec(min):
    if type(min) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError("Can't convert min to sec. Duration (min) format is not correct")
    else:
        return min * 60


def ms_to_min(ms):
    if type(ms) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError("Can't convert ms to min. Duration (ms) format is not correct")
    else:
        return ms / 60000