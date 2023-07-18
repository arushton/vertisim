import numpy
from math import sin, cos, atan2

class Wind:
    
    """Notes:
    Relevant changes in lines 928-935.
    """

    radius_earth = 6371 # km
    
    def windCorrectedVelocity(desired_speed: float, desired_heading: float, latitude: float, longitude: float, altitude: float) -> numpy.array:
        """Calculate the velocity requried to move the aircraft in the desired heading at the desired speed in the presence of wind.        
        
        Returns:
            numpy.array: Velocity vector required to move with the desired heading at the desired speed.
        """
        
        v_desired = Wind.headingToVector(desired_heading, magnitude=desired_speed)
        
        v_wind = Wind.windVector("head", desired_heading)
        
        return v_desired - v_wind
    
    def windVelocity(latitude: float, longitude: float, altitude: float) -> numpy.array:
        """Get the approximate wind speed at the given point (latitude, longitude, altitude above sea level)."""
        # TODO: implement, Rapid Refresh API
        pass
    
    def windVector(type: str, aircraft_heading: float) -> numpy.array:
        """Generate a wind vector relative to an aircraft (tailwind, crosswind, headwind).
        """
        wind_magnitude = 8.0 # m/s
        match type:
            case 'head':
                wind_heading = aircraft_heading + 180
            case 'cross':
                wind_heading = aircraft_heading + 90
            case 'tail':
                wind_heading = aircraft_heading
            case _ :
                wind_heading = 0
        return Wind.headingToVector(wind_heading, magnitude=wind_magnitude)
        
    def headingToVector(heading: float, magnitude: float = 1.0) -> numpy.array:
        """Converts a heading to a unit vector. Optional argument of vector magnitude.
        Heading is N=0, (+) direction = clockwise [i.e. aircraft_heading = 10° means 80° in polar where pos X = 0 and (+) direction = counterclockwise]."""

        # note that the vertical (northern, Y axis) component corresponds to cos(heading)
        return numpy.array([magnitude * sin(heading),
                            magnitude * cos(heading)])
        
    def latLongToHeading(latitude_1: float, longitude_1: float, latitude_2: float, longitude_2: float) -> float:
        """Find the heading of an aircraft moving from point A (latitude_1, longitude_1) to point B (latitude_2, longitude_2).
        Assumes the Earth is a spheroid - reasonable.
        
        Source:
            https://www.movable-type.co.uk/scripts/latlong.html
        """
        
        longitude_difference = longitude_2 - longitude_1
        return atan2(sin(longitude_difference) * cos(latitude_2), cos(latitude_1) * sin(latitude_2) - sin(latitude_1) * cos(latitude_2) * cos(longitude_difference))
    
    # --- UNUSED FUNCTIONS BELOW ---
        
    def xyVector(latitude_1: float, longitude_1: float, latitude_2: float, longitude_2: float) -> numpy.array:
        """Calculates the vector in the XY plane between point A (latitude_1, longitude_1) and B (latitude_2, longitude_2) where +X = East and +Y = North.
        """
        origin_point = Wind.latLongToXY(latitude_1, longitude_1)
        destination_point = Wind.latLongToXY(latitude_2, longitude_2)
        
        return destination_point - origin_point
        
    def latLongToXY(latitude: float, longitude: float) -> numpy.array:
        """Converts (latitude, longitude) to (x, y) where +X = East and +Y = North.
        Assumes the Earth is a spheroid - reasonable for short distances.
        """
        x = Wind.radius_earth * cos(latitude) * cos(longitude)
        y = Wind.radius_earth * cos(latitude) * sin(longitude)
        return numpy.array([x, 
                            y])
    