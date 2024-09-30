from typing import Dict
from ..aircraft.aircraft import AircraftStatus
from ..utils.helpers import current_and_lookahead_pax_count
import numpy as np
from ..utils.helpers import sec_to_ms
from collections import defaultdict

class ActionMask:
    def __init__(self, sim_setup, config: Dict):
        self.sim_setup = sim_setup
        self.config = config
    # Pre-cache frequently accessed attributes for faster access
        self.system_manager = self.sim_setup.system_manager
        self.aircraft_agents = self.system_manager.aircraft_agents
        self.num_aircraft = len(self.aircraft_agents)
        self.num_vertiports = self.sim_setup.num_vertiports()
        self.seat_capacity = self.sim_setup.aircraft_params['pax']
        self.vertiport_ids = self.sim_setup.vertiport_ids
        self.vertiport_id_to_index_map = self.sim_setup.vertiport_id_to_index_map
        self.vertiport_index_to_id_map = self.sim_setup.vertiport_index_to_id_map
        self.min_reserve_soc = self.config['aircraft_params']['min_reserve_soc']
        self.battery_capacity = self.config['aircraft_params']['battery_capacity']
        self.num_waiting_time_bins = self.config['sim_params']['quadratic_states']['waiting_time_bins']

    def get_action_mask(self, initial_state=False, final_state=False):
        """
        Create the action mask for the current state of the simulation.
        [Fly: list, Charge: int, Do nothing: int]
        
        Returns:
            List[int]: A flattened list representing the mask where 1 allows the action and 0 masks it.
        """
        
        # Cache SOC and charge increment configurations
        soc_increment_per_charge_event = self.config['external_optimization_params'].get('soc_increment_per_charge_event')
        charge_time_per_charge_event = self.config['external_optimization_params'].get('charge_time_per_charge_event')
        
        # Precompute flight_soc_required for all OD pairs to avoid redundant calculations
        flight_soc_required_map = {}
        average_energy_consumption = self.sim_setup.event_saver.average_energy_consumption_per_od_pair
        for od_pair, consumption in average_energy_consumption.items():
            flight_soc_required_map[od_pair] = (consumption['average'] / self.battery_capacity) * 100  # Percentage
        
        # Initialize the mask as a NumPy array for efficient operations
        # Each aircraft has (num_vertiports + 2) actions
        mask = np.zeros((self.num_aircraft, self.num_vertiports + 2), dtype=int)
        
        if initial_state:
            # All flight actions are masked (0), Charge and Do Nothing are allowed (1)
            mask[:, self.num_vertiports:self.num_vertiports+2] = 1
            return mask.flatten().tolist()
        
        if final_state:
            # Only Do Nothing is allowed (1), others are masked (0)
            mask[:, self.num_vertiports+1] = 1
            return mask.flatten().tolist()
        
        # Dictionaries to track enforced OD pairs and aircraft SoC
        enforced_od_pairs = set()
        aircraft_soc_map = {}  # {vertiport_id: [(aircraft_id, soc), ...]}

        # Calculate aircraft supply and demand at each vertiport
        aircraft_supply = {vertiport_id: 0 for vertiport_id in self.vertiport_ids}
        passenger_demand = {vertiport_id: 0 for vertiport_id in self.vertiport_ids}
        
        for aircraft in self.aircraft_agents.values():
            if aircraft.status == AircraftStatus.IDLE:
                aircraft_supply[aircraft.current_vertiport_id] += self.seat_capacity
        
        for vertiport in self.system_manager.vertiports.values():
            passenger_demand[vertiport.vertiport_id] = vertiport.get_total_waiting_passenger_count()

        
        # Check if there's any demand at the vertiports
        no_demand_in_system = not any(current_and_lookahead_pax_count(vertiport) for vertiport in self.system_manager.vertiports.values()) 

        # First pass: Determine initial masks and populate aircraft_soc_map
        for idx, (aircraft_id, aircraft) in enumerate(self.aircraft_agents.items()):
            current_vertiport_id = aircraft.current_vertiport_id
            current_vertiport = self.system_manager.vertiports[current_vertiport_id]
            
            # Determine SOC increment
            if soc_increment_per_charge_event is not None:
                soc_increment = self.config['aircraft_params']['soc_increment_per_charge_event']
            elif charge_time_per_charge_event is not None:
                charge_lookup_table = self.system_manager.aircraft_battery_models[current_vertiport_id]
                new_soc = aircraft.charging_strategy.calc_soc_from_charge_time(
                    charge_time=sec_to_ms(charge_time_per_charge_event),
                    initial_soc=aircraft.soc,
                    df=charge_lookup_table
                )
                soc_increment = new_soc - aircraft.soc
            else:
                raise ValueError("Invalid config for soc_increment_per_charge_event or charge_time_per_charge_event. One must be specified.")
            
            # Define conditions
            can_do_any = (
                aircraft.status == AircraftStatus.IDLE and 
                aircraft.soc <= 95 - soc_increment and 
                aircraft.soc > self.min_reserve_soc
            )
            
            can_fly_and_do_nothing = (
                aircraft.status == AircraftStatus.IDLE and
                aircraft.soc > 95 - soc_increment
            )
            
            # Initialize flight_mask and non_flight_actions
            if can_do_any:
                # Allow flying to any vertiport except the current one
                flight_mask = np.ones(self.num_vertiports, dtype=int)
                current_index = self.vertiport_id_to_index_map[current_vertiport_id]
                flight_mask[current_index] = 0  # Mask current vertiport
                non_flight_actions = [1, 1]  # Allow Charge and Do Nothing
                # Populate aircraft_soc_map for potential enforced flights
                aircraft_soc_map.setdefault(current_vertiport_id, []).append((idx, aircraft.soc))
            
            # If the aircraft is idle and its SoC is below the minimum reserve SoC + the minimum value in flight_soc_required dict, it can only charge
            elif aircraft.status == AircraftStatus.IDLE and aircraft.soc <= self.min_reserve_soc + min(flight_soc_required_map.values()):
                # Can only Charge
                flight_mask = np.zeros(self.num_vertiports, dtype=int)
                non_flight_actions = [1, 0]  # Allow Charge only
            elif can_fly_and_do_nothing:
                # Can Fly and Do Nothing
                flight_mask = np.ones(self.num_vertiports, dtype=int)
                current_index = self.vertiport_id_to_index_map[current_vertiport_id]
                flight_mask[current_index] = 0  # Mask current vertiport
                non_flight_actions = [0, 1]  # Allow Do Nothing only
                # Populate aircraft_soc_map for potential enforced flights
                aircraft_soc_map.setdefault(current_vertiport_id, []).append((idx, aircraft.soc))
            elif aircraft.status in [AircraftStatus.CHARGE, AircraftStatus.FLY, AircraftStatus.HOLD]:
                # Can only Do Nothing
                flight_mask = np.zeros(self.num_vertiports, dtype=int)
                non_flight_actions = [0, 1]  # Allow Do Nothing only
            else:
                raise ValueError(f"Invalid aircraft status: {aircraft.status}")
            
            # Disable flight actions to destinations that the aircraft cannot fly to based on SoC
            for dest_vertiport_id in self.vertiport_ids:
                if dest_vertiport_id == current_vertiport_id:
                    continue  # Already handled by masking current vertiport
                od_pair = f"{current_vertiport_id}_{dest_vertiport_id}"
                flight_soc_required = flight_soc_required_map.get(od_pair, 0) + self.min_reserve_soc
                if flight_soc_required > aircraft.soc:
                    dest_index = self.vertiport_id_to_index_map[dest_vertiport_id]
                    flight_mask[dest_index] = 0  # Mask the action

            # If there's no demand at any vertiport, allow only charge and Do Nothing
            if no_demand_in_system:
                flight_mask = np.zeros(self.num_vertiports, dtype=int)

            for dest_vertiport_id in self.vertiport_ids:
                if dest_vertiport_id == current_vertiport_id:
                    continue
                dest_index = self.vertiport_id_to_index_map[dest_vertiport_id]

                # If aircraft supply at destination is enough and no spill at origin
                if (aircraft_supply[dest_vertiport_id] >= passenger_demand[dest_vertiport_id] and 
                    not self.will_passengers_spill(current_vertiport)):
                    flight_mask[dest_index] = 0

            # If there's no demand at the destination and no spill at the origin
            expected_arrivals = current_vertiport.get_total_expected_pax_arrival_count()
            other_vertiports_expected_arrivals = sum(
                vertiport.get_total_expected_pax_arrival_count() 
                for v_id, vertiport in self.system_manager.vertiports.items() 
                if v_id != current_vertiport_id
            )
            if (expected_arrivals > 0 and 
                other_vertiports_expected_arrivals == 0 and 
                not self.will_passengers_spill(current_vertiport)):
                flight_mask[dest_index] = 0
            
            # Update the mask for the current aircraft
            mask[idx, :self.num_vertiports] = flight_mask
            mask[idx, self.num_vertiports:self.num_vertiports+2] = non_flight_actions


        # If waiting_time_bins is in the states of the simulation, use it to determine enforced flights
        if "waiting_time_bins" in self.config['sim_params']['simulation_states']['vertiport_states'] and self.config['sim_params']['algorithm'] not in ['RandomPolicy', 'VertiSimHeuristics']:            
            # Second pass: Process enforced flights and update masks
            for current_vertiport_id, aircraft_list in aircraft_soc_map.items():
                current_vertiport = self.sim_setup.vertiports[current_vertiport_id]
                
                for dest_vertiport_id in self.vertiport_ids:
                    if dest_vertiport_id == current_vertiport_id:
                        continue
                    
                    # passengers_in_last_bin = sum(waiting_time_bins[dest_vertiport_id][-int(self.num_waiting_time_bins/2):])
                    total_pax_count = current_vertiport.get_total_waiting_passenger_count()
                    # passengers_in_last_bin = waiting_time_bins[dest_vertiport_id][-1]
                    if (self.will_passengers_spill(current_vertiport) and (current_vertiport_id, dest_vertiport_id) not in enforced_od_pairs) \
                        or (total_pax_count >= self.seat_capacity and (current_vertiport_id, dest_vertiport_id) not in enforced_od_pairs):

                        dest_index = self.vertiport_id_to_index_map.get(dest_vertiport_id)
                        
                        # Find the aircraft with the highest SoC that can make the flight
                        suitable_aircraft = [
                            (idx, soc) for idx, soc in aircraft_list 
                            if soc >= flight_soc_required_map.get(f"{current_vertiport_id}_{dest_vertiport_id}", 0) + self.min_reserve_soc
                        ]
                        
                        if suitable_aircraft:
                            # Select the aircraft with the highest SoC
                            selected_idx, _ = max(suitable_aircraft, key=lambda x: x[1])
                            # Enforce the flight by allowing only the specific destination
                            enforced_od_pairs.add((current_vertiport_id, dest_vertiport_id))
                            
                            # Update the mask: allow only the enforced destination and mask all other actions
                            enforced_flight_mask = np.zeros(self.num_vertiports, dtype=int)
                            enforced_flight_mask[dest_index] = 1
                            mask[selected_idx, :self.num_vertiports] = enforced_flight_mask
                            mask[selected_idx, self.num_vertiports:self.num_vertiports+2] = [0, 0]  # Disable Charge and Do Nothing
                            
                            # Remove the aircraft from the list to prevent multiple assignments
                            aircraft_list.remove((selected_idx, _))
        
        # Convert the mask to a flattened list
        return mask.flatten().tolist()


    def will_passengers_spill(self, vertiport):
        """
        Check if passengers will spill at the vertiport.
        """
        waiting_time_bins = vertiport.get_pax_waiting_time_bins()
        spill_pax_count = sum(waiting_time_bins[vertiport.vertiport_id][-int(self.num_waiting_time_bins/2):])
        if spill_pax_count > 0:
            return True
        return False

