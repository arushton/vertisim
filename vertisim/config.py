import simpy
import random
from typing import Dict, Any
from collections import defaultdict
from utils.helpers import flatten


class VertiportConfig:

    def __init__(self,
                 env,
                 vertiport_layout: object,
                 vertiport_distances: str,
                 num_chargers: int,
                 shared_charger_sets: [Dict, None],
                 num_security_check_servers: int):
        self.env = env
        self.vertiport_layout = vertiport_layout
        self.vertiport_distances = vertiport_distances
        self.num_chargers = num_chargers
        self.shared_charger_sets = shared_charger_sets
        self.num_security_check_servers = num_security_check_servers

        self.fato_store = self.add_fato_ids_to_store()
        self.parking_space_store = self.check_charger_resource_type()
        self.taxiway_node_store = self.add_taxiway_nodes_to_store()
        self.edge_store = self.add_edges_to_store()
        self.charger_resource = simpy.Resource(self.env, capacity=num_chargers)
        self.waiting_room_stores = self.create_waiting_room_stores()
        self.available_aircraft_store = simpy.Store(self.env)

    def check_charger_resource_type(self):
        # Based on the charger resource specification, this method changes the structure of the parking pads.
        if self.shared_charger_sets and self.num_chargers is None:
            raise ValueError("Both shared_charger_sets and num_chargers variables are None. Please input one.")
        elif self.shared_charger_sets is not None:
            # If the user specified a shared chargers create a ParkingPadAndChargerResource object for each parking pad
            return self.add_parking_spaces_and_chargers_to_store(self.shared_charger_sets)
        elif self.num_chargers is not None:
            # If the user didn't specify a shared charger resources then all of the chargers can be used by any of the
            # parking pads
            return self.add_parking_spaces_to_store()

    def create_charger_resources(self, chargers_set: [Dict, int]) -> Dict:
        charger_resources = defaultdict(dict)
        if isinstance(chargers_set, dict):
            for shared_charger_list in chargers_set.values():
                charger_resources[simpy.Resource(self.env, capacity=1)] = shared_charger_list
            return charger_resources

        elif isinstance(chargers_set, int):
            for charger in range(chargers_set):
                charger_resources[simpy.Resource(self.env, capacity=1)] = charger
            return charger_resources
        else:
            raise TypeError("Charger set input type is not correct")

    def add_parking_spaces_and_chargers_to_store(self, chargers_set):
        # Add parking space IDs to parking_space_store
        if self.vertiport_layout.num_parking_pad == 0:
            #TODO: Currently, the simulator requires parking pad to store aircraft.
            # It should be able to store (park) the aircraft on the FATO if there are no parking spaces defined.
            print("Currently, skyport simulator is not able to run without a parking pad.")
            return
        # Create a store for parking spaces
        parking_space_store = simpy.Store(self.env, capacity=self.vertiport_layout.num_parking_pad)
        # Create a dictionary for the shared charger combination.
        shared_charger_resources = self.create_charger_resources(self.shared_charger_sets)
        for parking_pad_id in self.vertiport_layout.parking_pad_ids:
            parking_pad = ParkingPadAndChargerResource(parking_space_id=parking_pad_id)

            if not isinstance(chargers_set, dict):
                raise TypeError("Charger set type is not correct.")

            for charger_resource, parking_pad_id_list in shared_charger_resources.items():
                if parking_pad_id in parking_pad_id_list:
                    parking_pad.charger_resources.append(charger_resource)
            parking_space_store.put(parking_pad)
        return parking_space_store

    def add_parking_spaces_to_store(self):
        if self.vertiport_layout.num_fato == 0 and self.vertiport_layout.num_parking_pad == 0:
            raise ValueError("There is no FATO and parking pad in the skyport layout.")

        # If there is no parking space is defined then use FATO as parking space
        if self.vertiport_layout.num_parking_pad == 0:
            parking_space_store = self.add_fato_ids_to_store()
            return parking_space_store
        # Add parking space IDs to parking_space_store
        # Create a store for parking spaces
        parking_space_store = simpy.Store(self.env, capacity=self.vertiport_layout.num_parking_pad)
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
        for key, value in self.vertiport_distances.items():
            waiting_room_stores[f'waiting_room_{key}'] = simpy.Store(self.env)
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
        self.fato_id = fato_id
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
        self.parking_space_id = parking_space_id
        self.charger_resources = []
