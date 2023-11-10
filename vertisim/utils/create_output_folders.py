from pathlib import Path
import os
from .helpers import get_absolute_path

cwd = Path.cwd()

def create_output_folders(output_folder_path):
    """
    Creates the output folder
    """
    # Create output folder
    # if output_folder_path is None:
    #     output_folder_path = get_absolute_path(f'{str(cwd.parent.parent)}/output/test_only_aircraft')

    # if not os.path.exists(output_folder_path):
    #     os.makedirs(output_folder_path)
    
    # Create a log folder
    if not os.path.exists(get_absolute_path(f'{output_folder_path}/logs')):
        os.makedirs(get_absolute_path(f'{output_folder_path}/logs'))

    return output_folder_path