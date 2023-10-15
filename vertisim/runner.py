from vertisim import VertiSim
import json
import simpy

def runner():
    with open("vertisim/config.json", 'r') as f:
        config = json.load(f)


    env = simpy.Environment()
    vertisim = VertiSim(env, config)
    vertisim.run()

if __name__ == '__main__':
    runner()