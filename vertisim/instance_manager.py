from vertisim import VertiSim

class InstanceManager:
    def __init__(self, env, config, reward_function_parameters):
        self.env = env
        self.config = config
        self.reward_function_parameters = reward_function_parameters
        self.sim_instance = VertiSim(
            env=self.env, 
            config=self.config, 
            reward_function_parameters=self.reward_function_parameters
        )
        self.status = True
    
    def reset(self):
        self.status = False
        self.sim_instance.reset()
        self.sim_instance = VertiSim(
            env=self.env, 
            config=self.config, 
            reward_function_parameters=self.reward_function_parameters
        )
        self.status = self.sim_instance.status
    
    def get_initial_state(self):
        return self.sim_instance.get_initial_state()
    
    def step(self, actions):
        return self.sim_instance.step(actions)
