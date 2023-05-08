import logging
import datetime

class SimulatorTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        simulator_time = get_simulator_time()  # Replace this with the actual function to get the simulator's time

        # Convert the simulator time to a datetime object
        dt_object = datetime.datetime.fromtimestamp(simulator_time)

        if datefmt:
            return dt_object.strftime(datefmt)
        else:
            return str(dt_object)
