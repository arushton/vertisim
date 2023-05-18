from utils.get_state_variables import get_state_variables

def run_step_by_step_simulation(env, vertiports, airspace, structural_entity_groups, vertiport_manager, max_sim_time):
    while env.peek() < max_sim_time:
        env.step()
        get_simulation_state_variables(vertiports=vertiports, airspace=airspace, vertiport_manager=vertiport_manager)
        modify = get_user_input()
        if modify.isdigit():
            fast_forward_simulation(env=env, steps=int(modify))
        elif modify.lower() == "y":
            modify_aircraft_state(env=env, structural_entity_groups=structural_entity_groups, airspace=airspace, vertiport_manager=vertiport_manager)


def get_simulation_state_variables(vertiports, airspace, vertiport_manager):
    get_state_variables(vertiports=vertiports, 
                        airspace_states=airspace.airspace_resource_states,
                        aircraft_agents=vertiport_manager.aircraft_agents,
                        passenger_agents=vertiport_manager.passenger_agents)
    

def get_user_input():
    return input("Do you want to modify any aircraft's state? (y/n) or fast-forward simulation steps (# simulation steps to fast-forward): ")


def fast_forward_simulation(env, steps):
    for _ in range(steps):
        env.step()


def modify_aircraft_state(env, structural_entity_groups, airspace, vertiport_manager):
    aircraft_id, state, new_value = map(str.strip, input("Enter the aircraft id, state, and new value (comma separated): ").split(','))
    if aircraft_id in vertiport_manager.aircraft_agents:
        try_modify_state(env, aircraft_id, state, new_value, structural_entity_groups, airspace, vertiport_manager)
    else:
        print("Invalid aircraft id.")
        print("Valid aircraft ids are: ", list(vertiport_manager.aircraft_agents.keys()))


def try_modify_state(env, aircraft_id, state, new_value, structural_entity_groups, airspace, vertiport_manager):
    aircraft = vertiport_manager.aircraft_agents[aircraft_id]
    if hasattr(aircraft, state):
        update_state(env, aircraft, state, new_value, structural_entity_groups, airspace, vertiport_manager)
    else:
        print(f"Aircraft does not have a state named '{state}'")


def update_state(env, aircraft, state, new_value, structural_entity_groups, airspace, vertiport_manager):
    try:
        new_value = convert_new_value(state, new_value)
        setattr(aircraft, state, new_value)
        update_location_state(env, aircraft, state, new_value, structural_entity_groups, airspace, vertiport_manager)
        print(f"Successfully modified aircraft {aircraft.tail_number}'s state '{state}' to {new_value}")
    except ValueError as e:
        print(e)


def convert_new_value(state, new_value):
    if state == 'soc':
        return int(new_value)
    elif state in ['speed', 'priority', 'serviced_time_at_the_location']:
        return float(new_value)
    else:
        return new_value


def update_location_state(env, aircraft, state, new_value, structural_entity_groups, airspace, vertiport_manager):
    if state == 'location':
        if new_value in structural_entity_groups['fato']:
            update_aircraft_fato(env, aircraft, new_value, vertiport_manager)
        elif new_value in structural_entity_groups['parking_pad']:
            update_aircraft_parking_pad(env, aircraft, new_value, vertiport_manager)
        elif new_value in list(airspace.airlink_resources[aircraft.flight_direction].keys())[:-1]:
            update_aircraft_location(env, aircraft, new_value)


def update_aircraft_fato(env, aircraft, new_value, vertiport_manager):
    aircraft.assigned_fato_id = new_value
    env.process(vertiport_manager.fato_and_parking_pad_usage_process(aircraft=aircraft))

def update_aircraft_parking_pad(env, aircraft, new_value, vertiport_manager):
    aircraft.parking_space_id = new_value
    env.process(vertiport_manager.fato_and_parking_pad_usage_process(aircraft=aircraft))

def update_aircraft_location(env, aircraft, new_value):
    aircraft.location = new_value
    env.process(aircraft.fly_in_the_airspace(user_modification=True))

