import numpy as np
from math import sin, cos, tan, asin, atan2, pi

class Wind:
    
    """Relevant usage in:
        lines 932-947 of aircraft.py
    """

    RADIUS_EARTH = 6371 # km
    
    def ground_velocity(true_air_velocity: np.ndarray, v_wind: np.ndarray) -> np.ndarray:
        """Calculate the ground velocity."""
        return np.add(true_air_velocity, v_wind)
    
    def velocity_wind_adjusted(true_airspeed: float, desired_heading: float, v_wind: np.ndarray, ground_speed_threshold: float = None) -> np.ndarray:
        """Calculate the true velocity required to move the aircraft in the desired heading, in the presence of wind.
        Heading of the aircraft may change. True airspeed not adjusted unless < threshold. """
        
        wind_mag = Wind.magnitude(v_wind)
        wind_dir = Wind.vector_heading(v_wind)
        
        constant_term = (wind_mag * cos(wind_dir) - tan(desired_heading) * wind_mag * sin(wind_dir)) / true_airspeed
        
        required_heading = cos(-constant_term) - desired_heading
        
        true_vector = Wind.heading_to_vector(required_heading, true_airspeed)

        assert(Wind.vector_heading(true_vector) == Wind.vector_heading(desired_heading)), "Error. Formulism failed."
        
        if ground_speed_threshold and Wind.magnitude(Wind.ground_velocity(true_vector, v_wind)) < ground_speed_threshold:
            # TODO: calculate alternate vector
            print("ground speed less than threshold!")

        return true_vector
    
    def rta_velocity_wind_adjusted(desired_speed: float, desired_heading: float, v_wind: np.ndarray) -> np.ndarray:
        """Calculate the true velocity requried to move the aircraft in the desired heading at the desired speed, in the presence of wind. 
        True airspeed and initial heading of the aircraft may change.       
        
        Returns:
         np.array: Velocity vector required to move with the desired heading at the desired speed.
        """
        
        v_desired = Wind.heading_to_vector(desired_heading, magnitude=desired_speed)
        
        return np.subtract(v_desired, v_wind)
    
    def make_wind_vector(aircraft_heading: float, desired_wind_angle: float, wind_magnitude: float = 8.0) -> np.ndarray:
        """Generate a wind vector with a desired angle (radians) relative to the aircraft's heading 
         (0 = tailwind, 0.5pi = starboard crosswind, pi = headwind, 1.5pi = port crosswind).
        """
        
        assert(desired_wind_angle in range(0, 2 * pi)), "Angle must be in radians, and between 0 and 2pi."
    
        wind_heading = desired_wind_angle + aircraft_heading
                
        return Wind.heading_to_vector(wind_heading, magnitude=wind_magnitude)
        
    def heading_to_vector(heading: float, magnitude: float = 1.0) -> np.ndarray:
        """Converts a heading to a unit vector. Optional argument of vector magnitude.
        Heading is N=0, (+) direction = clockwise [i.e. aircraft_heading = 10° means 80° in polar where pos X = 0 and (+) direction = counterclockwise]."""

        if not heading:
            return np.array([0, 0])

        # note that the vertical (y axis) component corresponds to cos(heading)
        return np.array([magnitude * sin(heading),
                            magnitude * cos(heading)])
        
    def lat_long_to_heading(latitude_1: float, longitude_1: float, latitude_2: float, longitude_2: float) -> float:
        """Find the heading of an aircraft moving from point A (latitude_1, longitude_1) to point B (latitude_2, longitude_2).
        Assumes the Earth is a spheroid - reasonable.
        
        Source:
            https://www.movable-type.co.uk/scripts/latlong.html
        """
        
        longitude_difference = longitude_2 - longitude_1
        return atan2(sin(longitude_difference) * cos(latitude_2), cos(latitude_1) * sin(latitude_2) - sin(latitude_1) * cos(latitude_2) * cos(longitude_difference))
    
    def vector_heading(vector: np.ndarray) -> float:
        """Calculate the angle (radians) from North (positive Y axis) of any XY vector."""
        x, y = vector[0], vector[1]
        return atan2(x, y)
    
    def magnitude(vector: np.ndarray):
        """Calculate magnitude of numpy vector."""
        return np.sqrt(np.dot(vector, vector))
    
    # --- NOT IMPLEMENTED (YET)
    
    def api_wind_velocity(latitude: float, longitude: float, altitude: float) -> np.ndarray:
        """Get the approximate wind speed at the given point (latitude, longitude, altitude above sea level)."""
        # TODO: implement, High Resolution Rapid Refresh API
        pass
    
    # --- UNUSED FUNCTIONS BELOW ---
        
    def xyVector(latitude_1: float, longitude_1: float, latitude_2: float, longitude_2: float) -> np.ndarray:
        """Calculates the vector in the XY plane between point A (latitude_1, longitude_1) and B (latitude_2, longitude_2) where +X = East and +Y = North.
        """
        origin_point = Wind.latLongToXY(latitude_1, longitude_1)
        destination_point = Wind.latLongToXY(latitude_2, longitude_2)
        
        return destination_point - origin_point
        
    def latLongToXY(latitude: float, longitude: float) -> np.ndarray:
        """Converts (latitude, longitude) to (x, y) where +X = East and +Y = North.
        Assumes the Earth is a spheroid - reasonable for short distances.
        """
        x = Wind.RADIUS_EARTH * cos(latitude) * cos(longitude)
        y = Wind.RADIUS_EARTH * cos(latitude) * sin(longitude)
        return np.array([x, 
                            y])
    