import simpy
import random
from typing import Dict, Any, Union, List, Optional
from collections import defaultdict
from .utils.helpers import flatten
from .charger_model import ChargerModel
from .aircraft.aircraft import AircraftStatus
import numpy as np
from enum import Enum
from .utils.units import ms_to_min
from pydantic import BaseModel

class EntitySubState(BaseModel):
    num_jobs_in_service: int
    num_jobs_in_queue: int

class VertiportStates(BaseModel):
    num_waiting_passengers: Dict[str, int]
    fato: Optional[EntitySubState] = None
    park: EntitySubState = None
    taxi: EntitySubState = None
    arrival_fix: EntitySubState
    departure_fix: EntitySubState
    num_aircraft: int
    num_flight_requests: int
    num_available_fato: int
    num_available_parking_pad: int
    total_passenger_waiting_time: float
    aircraft_status: Dict[int, int]

class VertiportConfig:

    def __init__(self,
                 env: simpy.Environment,
                 vertiport_id: Any,
                 vertiport_data: dict,
                 vertiport_layout: dict,
                 vertiport_ids: list):
        self.env = env
        self.vertiport_id = vertiport_id
        self.vertiport_data = vertiport_data
        self.vertiport_layout = vertiport_layout
        self.parking_pad_ids = vertiport_layout.parking_pad_ids
        self.vertiport_ids = vertiport_ids
        self.vertiport_index = self.map_vertiport_id_to_index(vertiport_id)        
        self.shared_charger_sets = self.vertiport_data['shared_charger_sets']
        self.charger_model = self.set_charger_model()
        self.fato_store = self.add_fato_ids_to_store()
        self.parking_space_store = self.check_charger_resource_type()
        self.taxiway_node_store = self.add_taxiway_nodes_to_store()
        self.edge_store = self.add_edges_to_store()
        self.charger_resource = simpy.Resource(self.env, capacity=self.vertiport_data['num_chargers'])
        self.waiting_room_stores = self.create_waiting_room_stores()
        self.available_aircraft_store = simpy.FilterStore(self.env)
        self.taxi_resource = simpy.Resource(self.env, capacity=1)
        self.arrival_fix_resource = simpy.Resource(self.env, capacity=self.vertiport_data['holding_unit_capacity'])
        self.departure_fix_resource = simpy.Resource(self.env, capacity=1)
        self.num_aircraft = 0
        self.aircraft_departure_queue_count = 0
        self.num_flight_requests = 0
        self.num_waiting_passengers = 0


    def is_node_vertiport_location(self, location):
        return (self.is_taxi_node_location(location) or 
                self.is_fato_location(location) or
                self.is_parking_pad_location(location))

    def is_taxi_node_location(self, location):
        return location in self.vertiport_layout.taxiway_node_ids
    
    def is_fato_location(self, location):
        return location in self.vertiport_layout.fato_ids

    def is_parking_pad_location(self, location):
        return location in self.parking_pad_ids
    
    def map_vertiport_id_to_index(self, vertiport_id: str) -> int:
        """
        Returns the index of the vertiport ID in the vertiport_ids list.
        """
        return self.vertiport_ids.index(vertiport_id)
    
    def get_parking_pad_availability(self):
        """
        Returns the number of available parking pads.
        """
        return len(self.parking_space_store.items)
    
    def get_parking_pad_queue_length(self):
        """
        Returns the number of aircraft in the parking queue.
        """
        return len(self.parking_space_store.get_queue)
    
    def get_num_fato(self):
        return len(self.fato_store.items)
    
    def get_fato_occupancy(self):
        return sum(fato.fato_resource.count for fato in self.fato_store.items)
    
    def get_fato_queue_length(self):
        return sum(len(fato.fato_resource.queue) for fato in self.fato_store.items)
    
    def get_total_passenger_waiting_time(self):
        total_waiting_time_min = 0
        for waiting_room_store in self.waiting_room_stores.values():
            for passenger in waiting_room_store.items:
                total_waiting_time_min += ms_to_min(self.env.now - passenger.waiting_room_arrival_time)
        return total_waiting_time_min
    
    def get_passenger_count(self):
        return sum(len(waiting_room_store.items) for waiting_room_store in self.waiting_room_stores.values())
    
    def get_aircraft_status(self, aircraft_agents) -> List:
        # For each aircraft, check if it's at the current vertiport.
        # If it is, get its status; if it's not, the status is 0.
        return {
            aircraft.tail_number: aircraft.status.value if self.is_parking_pad_location(aircraft.location) else 0
            for aircraft in aircraft_agents.values()
        }

    def get_vertiport_states(self, aircraft_agents):
        """
        Will be deprecated in the future.
        """
        entity_states = {'num_waiting_passengers': {}}

        for fato in self.fato_store.items:
            entity_states[fato.resource_id] = {'num_jobs_in_service': fato.fato_resource.count,
                                            'num_jobs_in_queue': len(fato.fato_resource.queue)}

        if self.parking_space_store is not None:
            entity_states['park'] = {'num_jobs_in_service': self.get_parking_pad_availability(),
                                    'num_jobs_in_queue': self.get_parking_pad_queue_length()}

        if self.taxiway_node_store is not None:
            entity_states['taxi'] = {'num_jobs_in_service': len(self.taxiway_node_store.items),
                                    'num_jobs_in_queue': len(self.taxiway_node_store.get_queue)}

        entity_states['arrival_fix'] = {'num_jobs_in_service': self.arrival_fix_resource.count,
                                        'num_jobs_in_queue': len(self.arrival_fix_resource.queue)}

        entity_states['departure_fix'] = {'num_jobs_in_service': self.departure_fix_resource.count,
                                        'num_jobs_in_queue': len(self.departure_fix_resource.queue)}

        entity_states['num_aircraft'] = self.num_aircraft
        entity_states['num_flight_requests'] = self.num_flight_requests
        entity_states['num_available_fato'] = self.get_num_fato() - self.get_fato_occupancy()
        entity_states['num_available_parking_pad'] = self.get_parking_pad_availability()

        for destination, waiting_room_store in self.waiting_room_stores.items():
            entity_states['num_waiting_passengers'][f'to_{destination}'] = len(waiting_room_store.items)

        entity_states['total_passenger_waiting_time'] = self.get_total_passenger_waiting_time()

        entity_states['aircraft_status'] = self.get_aircraft_status(aircraft_agents)

        # Validate and serialize the data using Pydantic
        valid_entity_states = VertiportStates(**entity_states)

        # Return the validated data
        return valid_entity_states.dict()    


    def check_charger_resource_type(self):
        # Based on the charger resource specification, this method changes the structure of the parking pads.
        if self.vertiport_data['shared_charger_sets'] and self.vertiport_data['num_chargers'] is None:
            raise ValueError("Both shared_charger_sets and num_chargers variables are None. Please input one.")
        elif self.vertiport_data['shared_charger_sets'] is not None:
            # If the user specified a shared chargers create a ParkingPadAndChargerResource object for each parking pad
            return self.add_parking_spaces_and_chargers_to_store(self.vertiport_data['shared_charger_sets'])
        elif self.vertiport_data['num_chargers'] is not None:
            # If the user didn't specify a shared charger resources then all of the chargers can be used by any of the
            # parking pads
            return self.add_parking_spaces_to_store()

    def create_charger_resources(self, chargers_set: Union[Dict, int]) -> Dict:
        charger_resources = defaultdict(dict)
        if isinstance(chargers_set, dict):
            for shared_charger_list in chargers_set.values():
                charger_resources[simpy.Resource(self.env, capacity=1)] = shared_charger_list
            return charger_resources

        # elif isinstance(chargers_set, int):
        #     for charger in range(chargers_set):
        #         charger_resources[simpy.Resource(self.env, capacity=1)] = charger
        #     return charger_resources
        else:
            raise TypeError("Charger set input type is not correct")
        
    def set_charger_model(self):
        # This method sets the charger model for the chargers in the vertiport.
        return ChargerModel(charger_max_charge_rate=self.vertiport_data['charger_max_charge_rate'],
                            charger_efficiency=self.vertiport_data['charger_efficiency'])

    def add_parking_spaces_and_chargers_to_store(self):
        # Add parking space IDs to parking_space_store
        if self.vertiport_layout.num_parking_pad == 0:
            #TODO: Currently, the simulator requires parking pad to store aircraft.
            # It should be able to store (park) the aircraft on the FATO if there are no parking spaces defined.
            print("Currently, skyport simulator is not able to run without a parking pad.")
            return
        # Create a store for parking spaces
        parking_space_store = simpy.FilterStore(self.env, capacity=self.vertiport_layout.num_parking_pad)
        # Create a dictionary for the shared charger combination.
        shared_charger_resources = self.create_charger_resources(self.self.vertiport_data['shared_charger_sets'])

        # If no parking pad is defined then use FATO as parking pad
        if self.vertiport_layout.num_parking_pad == 0:
            for fato in self.vertiport_layout.fato_ids:
                parking_pad = ParkingPadAndChargerResource(parking_space_id=fato)
                for charger_resource, parking_pad_id_list in shared_charger_resources.items():
                    if fato in parking_pad_id_list:
                        parking_pad.charger_resources.append(charger_resource)
                parking_space_store.put(parking_pad)
            return parking_space_store

        for parking_pad_id in self.vertiport_layout.parking_pad_ids:
            parking_pad = ParkingPadAndChargerResource(parking_space_id=parking_pad_id)

            for charger_resource, parking_pad_id_list in shared_charger_resources.items():
                if parking_pad_id in parking_pad_id_list:
                    parking_pad.charger_resources.append(charger_resource)
            parking_space_store.put(parking_pad)
        return parking_space_store

    def add_parking_spaces_to_store(self):
        """
        Creates parking_space_store. If there is no parking space is defined then uses FATO as parking space
        """
        if self.vertiport_layout.num_fato == 0 and self.vertiport_layout.num_parking_pad == 0:
            raise ValueError("There is no FATO and parking pad in the skyport layout.")

        # If there is no parking space is defined then use FATO as parking space
        if self.vertiport_layout.num_parking_pad == 0:
            parking_space_store = simpy.FilterStore(self.env, capacity=self.vertiport_layout.num_fato)
            for fato in self.vertiport_layout.fato_ids:
                parking_pad = ParkingPadAndChargerResource(parking_space_id=fato)
                parking_space_store.put(parking_pad)
            return parking_space_store
        # Add parking space IDs to parking_space_store
        # Create a store for parking spaces
        parking_space_store = simpy.FilterStore(self.env, capacity=self.vertiport_layout.num_parking_pad)
        for parking_pad_id in self.vertiport_layout.parking_pad_ids:
            parking_pad = ParkingPadAndChargerResource(parking_space_id=parking_pad_id)
            parking_space_store.put(parking_pad)
        return parking_space_store

    def add_fato_ids_to_store(self):
        if self.vertiport_layout.num_fato == 0:
            raise ValueError("There is no FATO in the skyport layout.")
        # Create a store for FATO pads
        fato_store = simpy.FilterStore(self.env, capacity=self.vertiport_layout.num_fato)
        # Add fato ids to fato_store
        for fato_id in self.vertiport_layout.fato_ids:
            # FATOs are PriorityResource to prioritize arrival or departure. Normally, the queueing rule in
            # this simulator is FIFO.
            fato_resourse = simpy.PriorityResource(self.env, 1)
            # Put the FATO resources to the fato store.
            fato_store.put(FatoResource(fato_id, fato_resourse))
        return fato_store

    def add_taxiway_nodes_to_store(self):
        # If the skyport layout has taxiway nodes create a store for them.
        if self.vertiport_layout.num_taxiway_nodes != 0:
            taxiway_node_store = simpy.FilterStore(self.env, capacity=self.vertiport_layout.num_taxiway_nodes)
            # Add node IDs to taxiwayRampNodeStore
            for node_id in self.vertiport_layout.taxiway_node_ids:
                taxiway_node_store.put(node_id)
            return taxiway_node_store

    def add_edges_to_store(self):
        # If the vertiport layout has edges create a store for them.
        if self.vertiport_layout.num_edges != 0:
            edge_store = simpy.FilterStore(self.env, capacity=self.vertiport_layout.num_edges)
            # Add edge IDs to edge store
            for edge_id in self.vertiport_layout.edge_ids:
                edge_store.put(set(edge_id))
            return edge_store

    def create_waiting_room_stores(self):
        waiting_room_stores = defaultdict(dict)
        # Create a store for waiting rooms
        exclude_origin = [dest for dest in self.vertiport_ids if dest != self.vertiport_id]
        for dest in exclude_origin:
            waiting_room_stores[dest] = simpy.Store(self.env)
        return waiting_room_stores


class TaxiOperationsConfig:
    # This configuration prevents the usage of taxi area while an aircraft takes off.
    is_simultaneous_taxi_and_take_off_allowed = True
    # is_simultaneous_taxi_and_landing_allowed = True


class FatoResource:
    """
    Creates an object to store a resourse with its ID. Simpy Resources doesn't
    have any identifying names/IDs. So, we need to create a new class to define IDs to resources.

    Attributes
    ----------
    fato_id : str
        ID of a FATO pad
    fato_resource : simpy Resource
        simpy resource for FATO pads
    """

    def __init__(self, fato_id, fato_resource):
        self.resource_id = fato_id
        self.fato_resource = fato_resource


class ParkingPadAndChargerResource:
    """
    Creates an object to store a parking pad with its ID and shared charger resource. Simpy Resources doesn't
    have any identifying names/IDs. So, we need to create a new class to define IDs to resources.

    Attributes
    ----------
    parking_space_id : str
        ID of a parking pad
    """

    def __init__(self, parking_space_id: str) -> str:
        self.resource_id = parking_space_id
        self.charger_resources = []
