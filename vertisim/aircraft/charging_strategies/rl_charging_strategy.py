from .base_charging_strategy import BaseChargingStrategy
from ...utils.units import ms_to_sec, sec_to_ms
from ...utils.helpers import check_magnitude_order, miliseconds_to_hms, careful_round
from ..aircraft import AircraftStatus

class RLChargingStrategy(BaseChargingStrategy):
    def get_charging_time(self, aircraft):
        """
        Get charging time - Two options: Constant charging time or draw a number from distribution
        """
        # charge_time = self.get_charge_time_from_soc(aircraft=aircraft, init_soc=aircraft.soc, target_soc=aircraft.soc + 2)
        charge_time = sec_to_ms(5*60)

        aircraft.event_saver.save_aircraft_charging_time(vertiport_id=aircraft.destination_vertiport_id,
                                                     charging_time=charge_time)
        aircraft.logger.debug(f"Started Charging: Aircraft {aircraft.tail_number} will charge for {round(ms_to_sec(charge_time)/60,2)} mins at {aircraft.destination_vertiport_id}. init_soc: {round(aircraft.soc, 2)}")
        
        return charge_time
    
    def get_charge_time_from_soc(self, aircraft: object, init_soc:int, target_soc: int) -> float:
        """
        Calculates the charge time required to reach the target soc level.

        Parameters
        ----------
        init_soc: int
            Initial soc level of the aircraft.
        target_soc: int
            Target soc level of the aircraft.

        Returns
        -------
        float
            Charge time required to reach the target soc level.
        """
        if check_magnitude_order(init_soc, target_soc):
            df = aircraft.system_manager.aircraft_battery_models[aircraft.destination_vertiport_id]
            init_soc_time = df[df.soc == round(init_soc)]['time_sec'].values[0]
            target_soc_time = df[df.soc == target_soc]['time_sec'].values[0]
            return sec_to_ms(target_soc_time - init_soc_time)
        else:
            aircraft.logger.error(f"Final soc level ({target_soc}) is greater than 100).")
            aircraft.system_manager.truncation_event.succeed()

    def charge_aircraft(self, aircraft: object, parking_space: object, shared_charger: bool = False) -> None:
        """
        If the charger configuration is fixed and share-limited, all of the chargers that a parking pad has access
        should be requested. We use chargers as a resource instead of simpy.Store or simpy.Filterstore because it's
        easier to follow which resource is being used by which aircraft.
        """
        aircraft.status = AircraftStatus.CHARGE
        # aircraft.system_manager.trigger_stopping_event(event_name="charging_start_event", id=aircraft.tail_number)

        # If the chargers are shared, request all of the chargers that the parking pad has access to.
        if shared_charger:
            used_charger_resource, selected_charging_request = self.handle_shared_charger(aircraft=aircraft,
                                                                                          parking_space=parking_space)
        else:
            used_charger_resource, selected_charging_request = self.request_charger(aircraft=aircraft)
            yield selected_charging_request

        self.start_charging_process(aircraft=aircraft)
        if not aircraft.charged_during_turnaround:
            idle_time = aircraft.env.now - aircraft.arrival_time
        else:
            idle_time = aircraft.env.now - aircraft.charging_end_time
        aircraft.idle_time += idle_time
        aircraft.save_process_time(event='idle', process_time=idle_time)
        aircraft.logger.info(f'Saved idle time of {miliseconds_to_hms(idle_time)} between arrival and charging for aircraft {aircraft.tail_number} at {aircraft.location}.')

        aircraft.detailed_status = 'charging'
        charge_time = self.get_charging_time(aircraft=aircraft)

        yield aircraft.env.timeout(round(charge_time))
        aircraft.save_process_time(event='charge', process_time=charge_time)
        aircraft.detailed_status = 'idle'
        self.end_charging_process(aircraft=aircraft)

        old_soc = aircraft.soc
        self.soc_charge_update(aircraft=aircraft, charge_time=charge_time)

        # Set the aircraft status to idle
        aircraft.status = AircraftStatus.IDLE 
        aircraft.system_manager.trigger_stopping_event(event_name="charging_end_event", id=aircraft.tail_number)

        # Release the charger resource that is used by the aircraft and the charging request
        self.release_charger_resource(used_charger_resource, selected_charging_request)
        # Set the charged_during_turnaround to True to avoid charging the aircraft again during the turnaround
        aircraft.charged_during_turnaround = True
        aircraft.logger.debug(f"Finished Charging: Aircraft {aircraft.tail_number} at {aircraft.destination_vertiport_id}. Previous SoC: {round(old_soc, 2)}, New SoC: {careful_round(aircraft.soc, 2)}")
