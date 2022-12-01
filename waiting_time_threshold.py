from scheduler import *


def check_passenger_max_waiting_time_threshold(env, max_waiting_time, aircraftCapacity, vertiport):
    while True:
        yield env.timeout(max_waiting_time)
        env.process(
            Scheduler(env, max_waiting_time, aircraftCapacity, vertiport).check_max_waiting_time_threshold()
        )
