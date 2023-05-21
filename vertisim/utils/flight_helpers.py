import numpy as np

G_CONSTANT = 9.80665  # m/s^2

def temperature(altitude: float) -> float:
    """
    Computes the temperature at a given altitude
    :param altitude: in m
    :return: temperature in K
    """
    return 288.16 - 6.5*10**-3 * altitude

def lift_induced_drag_coef(cd_0: float, ld_max: float) -> float:
    """
    From the paper:
    The promise of energy-efficient battery-powered urban aircraft
    """
    return 1 / (4*cd_0*ld_max**2)


def min_power_speed_for_climb_descend(atmosphere_condition: str, 
                                      altitude: float, 
                                      mtom: float, 
                                      cd_0: float, 
                                      wing_area: float, 
                                      ld_max: float) -> float:
    """
    From the paper:
    The promise of energy-efficient battery-powered urban aircraft   

    Parameters
    ----------
    atmosphere_condition : str
        'good' or 'bad'
    altitude : float
        altitude in m
    mtom : float
        maximum take-off mass in kg
    cd_0 : float
        zero-lift drag coefficient
    wing_area : float
        wing area in m^2
    ld_max : float
        maximum lift-to-drag ratio

    Returns
    -------
    float
        minimum power speed in m/s
    """
    weight_term = 2 * weight(mtom) / (rho(altitude, atmosphere_condition) * wing_area)
    drag_term = np.sqrt(lift_induced_drag_coef(cd_0, ld_max) / (3 * cd_0))
    return round(np.sqrt(weight_term * drag_term))

def max_range_speed(atmosphere_condition, altitude, mtom, cd_0, wing_area, ld_max):
    """
    From the paper:
    The promise of energy-efficient battery-powered urban aircraft    
    """    
    term1 = 2*weight(mtom) / (rho(altitude, atmosphere_condition) * wing_area)
    term2 = np.sqrt(lift_induced_drag_coef(cd_0=cd_0, ld_max=ld_max) / cd_0)    
    return round(np.sqrt(term1 * term2))


def weight(mass):
    """
    Computes the weight of an aircraft given its mass
    :param mass: in kg
    :return: weight in N
    """
    return round(mass * G_CONSTANT)

def rotor_disk_area(mtom, disk_load):
    """
    Computes the rotor disk area given the maximum take-off mass and the disk load
    :param mtom: in kg
    :param disk_load: in kg/m^2
    :return: rotor disk area in m^2
    """
    return mtom / disk_load

def atmosphere_params(condition: str):
    if condition == 'good':
        tgl = 288.15 # Ground temperature [K]
        dgl = 1.225 # Ground density [kg/m^3]
        return tgl, dgl
    elif condition == 'bad':
        tgl = 300 # Ground temperature [K]
        dgl = 0.974 # Ground density [kg/m^3]
        return tgl, dgl
    else:
        raise ValueError('Invalid atmosphere condition. Choose between "good" and "bad"')


def rho(altitude: float, atmosphere_condition: str='good'):
    """
    Computes the air density at a given altitude
    :param altitude: in m
    :return: air density in kg/m^3
    """
    tgl, dgl = atmosphere_params(atmosphere_condition)
    return round(dgl * (temperature(altitude)/tgl)**((G_CONSTANT/(287*6.5*10**-3))-1), 4)


def stall_speed(atmosphere_condition, altitude, mtom, wing_area, cl_max):
    """
    Computes the stall speed of an aircraft given its mass
    :param mass: in kg
    :return: stall speed in m/s
    """
    return round(np.sqrt((2*weight(mtom))/(rho(altitude, atmosphere_condition)*wing_area*cl_max)))

