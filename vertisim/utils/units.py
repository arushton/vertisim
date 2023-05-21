import numpy as np


def sec_to_ms(sec):
    if sec is None:
        return None
    elif type(sec) not in [int, float, np.float64, np.float32, np.int_, np.int32]:
        raise TypeError(f"Can't convert sec to ms. Duration (sec) format is not correct. The type you inputted is {type(sec)}")
    else:
        return sec * 1000


def min_to_sec(min):
    if min is None:
        return None
    if type(min) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert min to sec. Duration (min) format is not correct. The type you inputted is {type(min)}")
    else:
        return min * 60


def ms_to_min(ms):
    if ms is None:
        return None
    if type(ms) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert ms to min. Duration (ms) format is not correct. The type you inputted is {type(ms)}")
    else:
        return ms / 60000
    
def sec_to_min(sec):
    if sec is None:
        return None
    if type(sec) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert sec to min. Duration (sec) format is not correct. The type you inputted is {type(sec)}")
    else:
        return sec / 60
    
def ms_to_sec(ms):
    if ms is None:
        return None
    if type(ms) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert ms to sec. Duration (ms) format is not correct. The type you inputted is {type(ms)}")
    else:
        return ms / 1000
    
def hr_to_ms(hr):
    if hr is None:
        return None
    if type(hr) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert hr to ms. Duration (hr) format is not correct. The type you inputted is {type(hr)}")
    else:
        return hr * 3600000
    
def sec_to_hr(sec):
    if sec is None:
        return None
    if type(sec) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert sec to hr. Duration (sec) format is not correct. The type you inputted is {type(sec)}")
    else:
        return sec / 3600

def ft_to_m(ft):
    if ft is None:
        return None
    if type(ft) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert ft to m. Altitude (ft) format is not correct. The type you inputted is {type(ft)}")
    else:
        return ft * 0.3048
    
def m_to_ft(m):
    if m is None:
        return None
    if type(m) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert m to ft. Altitude (m) format is not correct. The type you inputted is {type(m)}")
    else:
        return m / 0.3048

def miles_to_m(miles):
    if miles is None:
        return None
    if type(miles) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert miles to m. Distance (miles) format is not correct. The type you inputted is {type(miles)}")
    else:
        return miles * 1609.34
    
def mph_to_metersec(mph):
    if type(mph) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert mph to m/s. Speed (mph) format is not correct. The type you inputted is {type(mph)}")
    else:
        return mph * 0.44704
    
def metersec_to_mph(metersec):
    if type(metersec) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert m/s to mph. Speed (m/s) format is not correct. The type you inputted is {type(metersec)}")
    else:
        return metersec / 0.44704
    

def watt_to_kw(watt):
    if type(watt) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert watt to kw. Power (watt) format is not correct. The type you inputted is {type(watt)}")
    else:
        return watt / 1000
    

def kw_to_watt(kw):
    if type(kw) not in [int, float, np.float64, np.float32, np.int_]:
        raise TypeError(f"Can't convert kw to watt. Power (kw) format is not correct. The type you inputted is {type(kw)}")
    else:
        return kw * 1000
    
    