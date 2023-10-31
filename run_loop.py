import json
import subprocess
from math import pi
import numpy as np

# Load the existing config.json into a Python dictionary
with open('vertisim/config.json', 'r') as f:
    config = json.load(f)

wind_magnitudes = [0, 5, 10, 15, 20]
wind_angles = np.arange(0, 2*pi, 10 * pi / 180)  # Angles in radians

# Loop through each combination of wind_magnitude and wind_angle
for magnitude in wind_magnitudes:
    for angle in wind_angles:
        print(f"Running simulation with wind_magnitude={magnitude} and wind_angle={angle} radians")
        
        # Update the config dictionary with new values
        config['airspace_params']['wind_magnitude'] = magnitude
        config['airspace_params']['wind_angle'] = angle

        # Write the updated config back to config.json
        with open('vertisim/config.json', 'w') as f:
            json.dump(config, f, indent=4)

        # Run the vertisim.runner module
        result = subprocess.run(['python', '-m', 'vertisim.runner', '--config', 'vertisim/config.json'])
        if result.returncode != 0:
            print(f"An error occurred when running the simulation with wind_magnitude={magnitude} and wind_angle={angle}. Return code: {result.returncode}")
