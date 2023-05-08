import logging
import os
from utils.sim_time_formatter import SimulatorTimeFormatter

def setup_logging(log_level=logging.INFO, log_file=None):
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    formatter = SimulatorTimeFormatter(log_format, datefmt=date_format)  # Create an instance of the custom formatter

    if log_file:
        if not os.path.exists(os.path.dirname(log_file)):
            os.makedirs(os.path.dirname(log_file))
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler()

    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)
