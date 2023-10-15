import numpy as np
from math import sin, cos, asin, atan2, pi
from typing import Dict, List, Union
from utils.process_wind_data import WindDataProcessor
from utils.units import ms_to_hr


class Wind:
    
    RADIUS_EARTH = 6371 # km

    """Relevant usage in:
        lines 894-935 of aircraft.py
    """

    def __init__(self, static_wind=True, wind_magnitude=0, wind_angle=0, wind_data_file_path=None):
        self.static_wind = static_wind
        if self.static_wind:
            self.wind_magnitude = wind_magnitude
            self.wind_angle = wind_angle
        else:
            self.wind_data_processor = WindDataProcessor(wind_data_file_path)
            
    @staticmethod
    def ground_velocity(true_air_velocity: np.ndarray, v_wind: np.ndarray) -> np.ndarray:
        """Calculate the ground velocity."""
        return np.add(true_air_velocity, v_wind)
    
    @staticmethod
    def wind_adjusted_true_velocity(cruise_speed: float, desired_heading: float, v_wind: np.ndarray, ground_speed_threshold: float = None) -> np.ndarray:
        """Calculate the true velocity required to move the aircraft in the desired heading, in the presence of wind.
        Heading of the aircraft may change. True airspeed not adjusted unless ground speed < threshold. 
        
        Central Equation: sin(a - c) = (|B| / |A|)sin(b - a), 
        where a = desired_heading, c = true_heading, b = wind_heading all relative to the x-axis (using swap_angle_relative_x_axis_north),
        and |B| = wind_mag and |A| = cruise_speed.
        """
        
        wind_mag = Wind.magnitude(v_wind)
        a = Wind.swap_angle_relative_x_axis_north(desired_heading)
        b = Wind.swap_angle_relative_x_axis_north(Wind.vector_to_heading(v_wind))
        B_over_A = wind_mag / cruise_speed
        right_hand_side = B_over_A * sin(b - a)
        c = a - asin(right_hand_side) # technically, c = a - asin(rhs) - 2pi * k
        required_heading = Wind.swap_angle_relative_x_axis_north(c)
        
        # new velocities
        true_velocity = Wind.heading_to_vector(required_heading, magnitude=cruise_speed)
        ground_velocity = Wind.ground_velocity(true_velocity, v_wind)
                
        # if ground_speed @ given true_airspeed < threshold, return the minimum true velocity needed to fly in the desired heading @ threshold
        if ground_speed_threshold and Wind.magnitude(ground_velocity) < ground_speed_threshold:
            return Wind.rta_velocity_wind_adjusted(ground_speed_threshold, desired_heading, v_wind)

        return true_velocity

    @staticmethod
    def rta_velocity_wind_adjusted(desired_speed: float, desired_heading: float, v_wind: np.ndarray) -> np.ndarray:
        """Calculate the true velocity requried to move the aircraft in the desired heading at the desired speed, in the presence of wind. 
        True airspeed and initial heading of the aircraft may change.       
        
        Returns:
         np.array: Velocity vector required to move with the desired heading at the desired speed.
        """
        
        v_desired = Wind.heading_to_vector(desired_heading, magnitude=desired_speed)
        
        return np.subtract(v_desired, v_wind)
    
    def make_static_wind_vector_relative_to_the_aircraft(self, aircraft_heading: float) -> np.ndarray:
        """Generate a wind vector with a desired angle (radians) relative to the aircraft's heading 
         (0 = tailwind, 0.5pi = starboard crosswind, pi = headwind, 1.5pi = port crosswind).
        """
        
        assert(0 <= self.wind_angle <= 2 * pi), "Angle must be in radians, and between 0 and 2pi."
    
        wind_heading = self.wind_angle + aircraft_heading
                
        return Wind.heading_to_vector(wind_heading, magnitude=self.wind_magnitude)

    def make_wind_vector_relative_to_north(self, wind_origin_heading: float, wind_magnitude: float = 8.0) -> np.ndarray:
        """Generate a wind vector coming from wind_origin_heading, where wind_origin_heading is relative to north.
        (0 = South wind, 0.5pi = West wind, pi = North wind, 1.5pi = East wind).
        """
        
        # Ensure angles are in the correct range
        assert(0 <= wind_origin_heading <= 2 * np.pi), f"Wind angle must be in radians, and between 0 and 2pi. Wind angle = {wind_origin_heading}"
        
        return Wind.heading_to_vector(wind_origin_heading + pi, magnitude=wind_magnitude)        

    @staticmethod   
    def heading_to_vector(heading: float, magnitude: float = 1.0) -> np.ndarray:
        """Converts a heading to a unit vector. Optional argument of vector magnitude.
        Heading is N=0, (+) direction = clockwise [i.e. aircraft_heading = 10° means 80° in polar where pos X = 0 and (+) direction = counterclockwise]."""

        # note that the vertical (y axis) component corresponds to cos(heading)
        return np.array([magnitude * sin(heading),
                            magnitude * cos(heading)])

    @staticmethod   
    def lat_long_to_heading(latitude_1: float, longitude_1: float, latitude_2: float, longitude_2: float) -> float:
        """Find the heading of an aircraft moving from point A (latitude_1, longitude_1) to point B (latitude_2, longitude_2).
        Assumes the Earth is a spheroid - reasonable.
        
        Source:
            https://www.movable-type.co.uk/scripts/latlong.html
        """
        
        longitude_difference = longitude_2 - longitude_1
        return atan2(sin(longitude_difference) * cos(latitude_2), cos(latitude_1) * sin(latitude_2) - sin(latitude_1) * cos(latitude_2) * cos(longitude_difference))
    
    @staticmethod
    def swap_angle_relative_x_axis_north(angle: float) -> float:
        """Converts an angle (radians) relative to the x-axis (CCW = pos) to be relative to North (CW = pos), and vice versa."""
        if angle <= pi / 2:
            return (pi / 2) - angle
            
        return (5 * pi / 2) - angle
        
    @staticmethod
    def vector_to_heading(vector: np.ndarray) -> float:
        """Returns the angle of the vector relative to the positive Y-axis (North) in radians."""
        
        # angle relative to x axis
        angle_from_x = atan2(vector[1], vector[0])
        
        return Wind.swap_angle_relative_x_axis_north(angle_from_x) 
    
    @staticmethod
    def magnitude(vector: np.ndarray):
        """Calculate magnitude of numpy vector."""
        return np.sqrt(np.dot(vector, vector))
    
    @staticmethod
    def convert_to_range_zero_to_two_pi(angle: float, epsilon=1e-9):
        """Bring an angle (radians) into the range [0, 2pi)."""
        
        while angle > 2 * pi:
            angle -= 2 * pi
        while angle < 0:
            angle += 2 * pi
            
        if abs(angle - 2 * pi) < epsilon:
            return 0
    
        return angle
    
    # --- VERIFICATION -- 
    @staticmethod
    def verify_aircraft_heading(ground_v: np.ndarray, destination_heading: float) -> None:
        aircraft_heading = Wind.convert_to_range_zero_to_two_pi(Wind.vector_to_heading(ground_v))
        destination_heading = Wind.convert_to_range_zero_to_two_pi(destination_heading)
        assert abs(aircraft_heading - destination_heading) < 1e-9, f'Wrong direction. Aircraft heading = {aircraft_heading}, Destination Heading = {destination_heading}.'
    
    @staticmethod
    def verify_aircraft_speeds(ground_v: np.ndarray, ground_threshold: float, cruise_speed: float, true_airspeed_v: np.ndarray):
        ground_speed = Wind.magnitude(ground_v)
        assert ground_speed > ground_threshold or abs(ground_speed - ground_threshold) < 1e-9, f'Aircraft is not flying fast enough. Ground speed = {ground_speed}. Minimum = {ground_threshold}.'
        if not (abs(ground_speed - ground_threshold) < 1e-9): # the aircraft was able to maintain its heading flying @ true_airspeed
            true_airspeed = Wind.magnitude(true_airspeed_v)
            assert abs(true_airspeed - cruise_speed) < 1e-9, f'Aircraft true airspeed is not equal to cruise speed. Cruise speed = {cruise_speed}, True airspeed = {true_airspeed}.'

    # --- WIND SPEED / DIR GETTERS ---

    def get_static_wind_data(self) -> Dict[str, Union[float, int]]:
        """
        Returns static wind data if available.
        
        Returns:
            dict: A dictionary containing wind magnitude and wind angle.
        """
        return {'wind_magnitude': self.wind_magnitude, 'wind_angle': self.wind_angle}
    
    def fetch_wind_states(self, locations: List[str]) -> Dict[str, Dict[str, Union[float, int]]]:
        """
        Retrieves wind data for given locations. Returns static wind data if it's enabled.
        
        Args:
            locations (List[str]): List of locations to fetch the wind data for.
        
        Returns:
            dict: A dictionary containing wind data for each location.
            
        Raises:
            ValueError: If unique locations in the wind data don't match with the provided locations list.
        """
        if self.static_wind:
            return self.get_static_wind_data()

        unique_locations = self.wind_data_processor.wind_data['locationname'].unique().tolist()

        if set(locations) != set(unique_locations):
            raise ValueError(
                f'Locations in the wind data do not match with the vertiport locations list. '
                f'Locations in the wind data = {unique_locations}, Vertiport locations list = {locations}.'
            )

        return {
            location_id: self.get_time_and_location_specific_wind_states(
                time_of_day=int(ms_to_hr(self.env.now)), 
                location=location_id
            )
            for location_id in locations
        }

    def get_time_and_location_specific_wind_states(self, time_of_day: int, location: str) -> Dict:
        """
        Retrieves wind data for a specific time and location.
        
        Args:
            time_of_day (int): The specific hour of the day.
            location (str): The desired location for wind data retrieval.
        
        Returns:
            dict: A dictionary containing wind data for the specified time and location.
        """        
        return self.wind_data_processor.get_time_and_location_specific_wind_states(time_of_day, location)
    
    # --- UNUSED FUNCTIONS BELOW ---

    @staticmethod   
    def xyVector(latitude_1: float, longitude_1: float, latitude_2: float, longitude_2: float) -> np.ndarray:
        """Calculates the vector in the XY plane between point A (latitude_1, longitude_1) and B (latitude_2, longitude_2) where +X = East and +Y = North.
        """
        origin_point = Wind.latLongToXY(latitude_1, longitude_1)
        destination_point = Wind.latLongToXY(latitude_2, longitude_2)
        
        return destination_point - origin_point
    
    @staticmethod    
    def latLongToXY(latitude: float, longitude: float) -> np.ndarray:
        """Converts (latitude, longitude) to (x, y) where +X = East and +Y = North.
        Assumes the Earth is a spheroid - reasonable for short distances.
        """
        x = Wind.RADIUS_EARTH * cos(latitude) * cos(longitude)
        y = Wind.RADIUS_EARTH * cos(latitude) * sin(longitude)
        return np.array([x, 
                            y])
    