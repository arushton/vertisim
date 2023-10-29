import logging
import os
from .utils.helpers import miliseconds_to_hms
import datetime
import time


class CustomFormatter(logging.Formatter):
    def __init__(self, fmt, env):
        super().__init__(fmt)
        self.env = env  # store the environment

    def formatTime(self, record, datefmt=None):
        simulation_time = self.env.now
        return miliseconds_to_hms(simulation_time)

    def format(self, record):
        if not hasattr(record, 'tail_number'):
            record.tail_number = ''
        if not hasattr(record, 'location'):
            record.location = ''
        if not hasattr(record, 'soc'):
            record.soc = ''
        if not hasattr(record, 'event'):
            record.event = ''
        return super().format(record)


class Logger:
    def __init__(self, output_folder_path):
        self.output_folder_path = output_folder_path
        self.logger = None

    def create_logger(self, name, env, level=logging.DEBUG):
        log_file = self.set_logfile_path(name)
        handler = logging.FileHandler(log_file)
        formatter = CustomFormatter('%(asctime)s %(levelname)s %(tail_number)s %(location)s %(event)s %(message)s', env)
        handler.setFormatter(formatter)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.addHandler(handler)

    def set_logfile_path(self, name):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        if not os.path.exists(f'{self.output_folder_path}/logs/{name}'):
            os.makedirs(f'{self.output_folder_path}/logs/{name}')
        return f'{self.output_folder_path}/logs/{name}/{name}_{timestamp}.log'

    def debug(self, *args, **kwargs):
        if self.logger is None:
            raise Exception('Logger not initialized. Call create_logger first.')
        return self.logger.debug(*args, **kwargs)
    
    def info(self, *args, **kwargs):
        if self.logger is None:
            raise Exception('Logger not initialized. Call create_logger first.')
        return self.logger.info(*args, **kwargs)
    
    def warning(self, *args, **kwargs):
        if self.logger is None:
            raise Exception('Logger not initialized. Call create_logger first.')
        return self.logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        if self.logger is None:
            raise Exception('Logger not initialized. Call create_logger first.')
        return self.logger.error(*args, **kwargs)
    
    def critical(self, *args, **kwargs):
        if self.logger is None:
            raise Exception('Logger not initialized. Call create_logger first.')
        return self.logger.critical(*args, **kwargs)

    def remove_logs(self, seconds=10):
        current_time = time.time()
        for root, dirs, files in os.walk(self.output_folder_path):
            for file in files:
                if file.endswith('.log'):
                    file_path = os.path.join(root, file)
                    file_stat = os.stat(file_path)
                    creation_time = file_stat.st_ctime
                    if (current_time - creation_time) >= seconds: # seconds
                        os.remove(file_path)
