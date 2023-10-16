from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from ..vertisim.instance_manager import InstanceManager
from .models import create_action_models
import simpy
from .config import CONFIG  # Import the loaded configuration

app = FastAPI()

env = simpy.Environment()
reward_function_parameters = CONFIG["reward_function_parameters"]

instance_manager = InstanceManager(env=env,
                                   config=CONFIG,
                                   reward_function_parameters=reward_function_parameters)
Actions = create_action_models(instance_manager.sim_instance.get_vertiport_count())

@app.post("/reset")
async def reset():
    initial_state = instance_manager.reset()
    return {"initial_state": initial_state}

@app.post("/step")
async def step(actions: Actions):
    new_state, reward, terminated, truncated = instance_manager.step(actions.actions_list)
    return {
        "new_state": new_state,
        "reward": reward,
        "terminated": terminated,
        "truncated": truncated
    }

@app.get("/get_space_params")
async def get_space_params():
    # Extract and return the parameters needed to construct action 
    # and observation spaces in the RL algorithm.
    return {
        "n_actions": instance_manager.sim_instance.get_action_count(),
        "n_aircraft": instance_manager.sim_instance.get_aircraft_count(), 
        "n_vertiports": instance_manager.sim_instance.get_vertiport_count(),
        "n_vertiport_state_variables": instance_manager.sim_instance.get_vertiport_state_variable_count(),
        "n_aircraft_state_variables": instance_manager.sim_instance.get_aircraft_state_variable_count(),
        "n_environmental_state_variables": instance_manager.sim_instance.get_environmental_state_variable_count()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000) 

