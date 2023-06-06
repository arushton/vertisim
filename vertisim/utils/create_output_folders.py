from pathlib import Path
import os

cwd = Path.cwd()

def create_output_folders(output_folder_path):
    """
    Creates the output folder
    """
    # Create output folder
    if output_folder_path is None:
        output_folder_path = f'{str(cwd.parent.parent)}/output/test_only_aircraft'

    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)
    
    # Create a log folder
    if not os.path.exists(f'{output_folder_path}/logs'):
        os.makedirs(f'{output_folder_path}/logs')

    return output_folder_path