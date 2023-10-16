import pandas as pd
import random
from typing import Dict
from ..utils.read_files import read_input_file
from ..utils.helpers import set_seed
from ..utils.units import mph_to_metersec, degrees_to_radians
from ..wind.wind_models import DynamicWindState
import datetime as dt


class WindDataProcessor:
    def __init__(self, file_path):
        self.wind_data = self._load_wind_data(file_path)
        self.wind_data_day = self.get_wind_data_for_random_day()

    @staticmethod
    def _load_wind_data(file_path):
        data = read_input_file(file_path)
        data['datetime'] = pd.to_datetime(data['datetime'])
        data['windspeed'] = data['windspeed'].apply(mph_to_metersec)
        data['winddir'] = data['winddir'].apply(degrees_to_radians)
        return data[['locationname', 'datetime', 'windspeed', 'winddir']]        

    def pick_random_day(self) -> dt.date:
        """
        Picks a random day from the wind data.
        """
        unique_days = self.wind_data['datetime'].dt.date.unique().tolist()
        set_seed(how='instant')
        return random.choice(unique_days)

    def get_wind_data_for_random_day(self):
        """
        Filters the wind data for a randomly selected day.
        """
        random_day = self.pick_random_day()
        mask = (self.wind_data['datetime'].dt.date == random_day)
        return self.wind_data[mask].reset_index(drop=True)
    
    def _get_filtered_data(self, time_of_day=None, location=None):
        mask = True
        if time_of_day is not None:
            mask &= self.wind_data_day['datetime'].dt.hour == time_of_day
        if location is not None:
            mask &= self.wind_data_day['locationname'] == location
        return self.wind_data_day[mask]    

    def get_time_specific_wind_states(self, time_of_day: int) -> Dict:
        data = self._get_filtered_data(time_of_day=time_of_day)
        if data.empty:
            raise ValueError(f'No wind data for {time_of_day}:00.')
        return {loc: {'windspeed': ws, 'winddir': wd} for loc, ws, wd in zip(data['locationname'], data['windspeed'], data['winddir'])}

    def get_location_specific_wind_states(self, location: str) -> Dict:
        data = self._get_filtered_data(location=location)
        if data.empty:
            raise ValueError(f'No wind data for {location}.')
        return {time: {'windspeed': ws, 'winddir': wd} for time, ws, wd in zip(data['datetime'], data['windspeed'], data['winddir'])}

    def get_time_and_location_specific_wind_states(self, time_of_day: int, location: str) -> Dict:
        data = self._get_filtered_data(time_of_day, location)
        if data.empty:
            raise ValueError(f'No wind data for {location} at {time_of_day}:00.')
        row = data.iloc[0]
        wind_state = DynamicWindState(locationname=location, windspeed=row['windspeed'], winddir=row['winddir'])
        return wind_state.dict()