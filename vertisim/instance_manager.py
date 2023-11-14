from vertisim.vertisim import VertiSim
import simpy

class InstanceManager:
    def __init__(self, config, reward_function_parameters):
        self.config = config
        self.reward_function_parameters = reward_function_parameters
        self.sim_instance = VertiSim(
            env=simpy.Environment(), 
            config=self.config, 
            reward_function_parameters=self.reward_function_parameters
        )
        self.status = True
    
    def reset(self):
        self.status = False
        # self.sim_instance.reset()
        self.sim_instance = VertiSim(
            env=simpy.Environment(), 
            config=self.config, 
            reward_function_parameters=self.reward_function_parameters
        )
        self.status = self.sim_instance.status
    
    def get_initial_state(self):
        return self.sim_instance.get_initial_state()
    
    def step(self, actions):
        return self.sim_instance.step(actions)
    
    def get_performance_metrics(self):
        return self.sim_instance.get_performance_metrics()
