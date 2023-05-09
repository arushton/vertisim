import numpy as np

def haversine_dist(lat1: float, lon1: float, lat2: float, lon2: float, unit: str = 'mile') -> float:
    # 6367 for distance in KM for miles use 3958
    if unit == 'km':
        r = 6367
    elif unit == 'mile':
        r = 3958
    elif unit == 'meter':
        r = 6367000
    else:
        raise ValueError('Unit must be either km, mile or meters.')

    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    
    d_lat = lat2_rad - lat1_rad
    d_lon = lon2_rad - lon1_rad
    a = np.sin(d_lat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(d_lon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return round(r * c)