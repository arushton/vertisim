import unittest
import numpy as np
from wind import Wind
from math import pi, cos, sin

class TestWind(unittest.TestCase):
    
    def test_make_wind_vector_relative_to_north(self):
        v_wind = Wind.make_wind_vector_relative_to_north(pi / 6, wind_magnitude=10.0) # S + 30 degrees W wind, 10.0 m / s 
        self.assertAlmostEqual(v_wind[0], -10 * sin(pi / 6), msg="Incorrect wind vector x-component.")
        self.assertAlmostEqual(v_wind[1], -10 * cos(pi / 6), msg="Incorrect wind vector y-component.")
        
    def test_magnitude(self):
        v = np.array([3, 4])
        mag = Wind.magnitude(v)
        self.assertAlmostEqual(mag, 5)
        
    def test_ground_v(self):
        v_wind = Wind.make_wind_vector_relative_to_north(pi / 4, wind_magnitude=10.0) # SW wind, 10.0 m / s 
        true_air_v = np.array([0, 50.0]) # north, 50.0 m / s
        gv = Wind.ground_velocity(true_air_v, v_wind)
        self.assertAlmostEqual(gv[0], -10 * sin(pi / 4), msg="Incorrect ground velocity x-component.")
        self.assertAlmostEqual(gv[1], 50 - 10 * cos(pi / 4), msg="Incorrect ground velocity y-component.")

    def test_vector_to_heading(self):
        # angle 1
        actual_heading = pi / 3 # from North
        vector = np.array([sin(actual_heading),
                           cos(actual_heading)]) # unit vector
        returned_heading = Wind.vector_to_heading(vector)
        self.assertAlmostEqual(returned_heading, actual_heading, msg="Heading incorrect.")
        # angle 2
        actual_heading = 3 * pi / 4 # from North
        vector = np.array([sin(actual_heading),
                           cos(actual_heading)]) # unit vector
        returned_heading = Wind.vector_to_heading(vector)
        self.assertAlmostEqual(returned_heading, actual_heading, msg="Heading incorrect.")
        # angle 3
        actual_heading = 7 * pi / 4 # from North
        vector = np.array([sin(actual_heading),
                           cos(actual_heading)]) # unit vector
        returned_heading = Wind.vector_to_heading(vector)
        self.assertAlmostEqual(returned_heading, actual_heading, msg="Heading incorrect.")

    def test_swap_angle_relative_x_axis_north(self):
        # angle_relative_x < pi / 2
        angle_relative_x = 3 * pi / 8
        angle_relative_N = (pi / 2) - angle_relative_x
        returned_angle_relative_N = Wind.swap_angle_relative_x_axis_north(angle_relative_x)
        self.assertAlmostEqual(angle_relative_N, returned_angle_relative_N, msg="Angle conversion failed.")
        # angle_relative_x  > pi / 2
        angle_relative_x = 7 * pi / 4
        angle_relative_N = 3 * pi / 4
        returned_angle_relative_N = Wind.swap_angle_relative_x_axis_north(angle_relative_x)
        self.assertAlmostEqual(angle_relative_N, returned_angle_relative_N, msg="Angle conversion failed.")
        # N --> x conversion
        angle_relative_x = 7 * pi / 4
        angle_relative_N = 3 * pi / 4
        returned_angle_relative_x = Wind.swap_angle_relative_x_axis_north(angle_relative_N)
        self.assertAlmostEqual(angle_relative_x, returned_angle_relative_x, msg="Angle conversion failed.")

    def test_wind_adjusted_true_velocity(self):

        # desired_heading relative to N
        for desired_heading in np.arange(0, 2*pi, 0.1):
            
            cruise_speed = 55 # m / s
            wind_mag = 10.0
            
            # wind_heading relative to N
            for wind_heading in np.arange(0, 2*pi, 0.1):
                
                wind_heading = pi / 4 # Coming from North + 45 degrees East
                v_wind = Wind.make_wind_vector_relative_to_north(wind_heading, wind_magnitude=wind_mag) # SW wind, 10.0 m / s 
                ground_speed_threshold = 30.0 # m / s
                
                true_velocity = Wind.wind_adjusted_true_velocity(cruise_speed, desired_heading, v_wind, ground_speed_threshold=ground_speed_threshold)
                true_airspeed = Wind.magnitude(true_velocity)
                
                ground_velocity = Wind.ground_velocity(true_velocity, v_wind)
                ground_heading = Wind.vector_to_heading(ground_velocity)
                ground_speed = Wind.magnitude(ground_velocity)
                
                self.assertAlmostEqual(ground_heading, desired_heading, places=2, msg=f'Aircraft\'s actual heading is not aligned with desired. Desired = {desired_heading}. Actual = {ground_heading}.')
                self.assertGreaterEqual(ground_speed, ground_speed_threshold, msg=f'Aircraft\'s ground speed is below the threshold. ')
                if ground_speed != ground_speed_threshold:
                    self.assertAlmostEqual(true_airspeed, cruise_speed, places=2, msg=f'Aircraft does not have true_airspeed = cruise_speed.')
                    
if __name__ == '__main__':
    unittest.main()