import gymnasium as gym
import utils
import numpy as np
import torch
from utils import pytorch_util as ptu
from agents.pg_agent import PGAgent
import time
import os
from environments.vertisim_env import VertiSimEnv

import sys
from pathlib import Path

# Get the path to 'VertiSim_dev' directory
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
# Add the 'VertiSim_dev' directory to Python path
# sys.path.append(str(vertsdev_path))


def run_training_loop(args):

    # TODO: Implement this
    # logger = Logger(args.logdir)
    print(sys.path)

    # set random seeds
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    ptu.init_gpu(use_gpu=not args.no_gpu, gpu_id=args.which_gpu)    

    # Create the environment
    config_file_path = "../vertisim/config.json"
    env = gym.make("VertiSim", config_file_path=config_file_path)
    discrete = isinstance(env.action_space, gym.spaces.Discrete)

    max_ep_len = args.ep_len or env.spec.max_episode_steps

    ob_dim = env.observation_space.shape[0]
    ac_dim = env.action_space.n if discrete else env.action_space.shape[0]

    # initialize agent
    agent = PGAgent(
        ob_dim,
        ac_dim,
        discrete,
        n_layers=args.n_layers,
        layer_size=args.layer_size,
        gamma=args.discount,
        learning_rate=args.learning_rate,
        use_baseline=args.use_baseline,
        use_reward_to_go=args.use_reward_to_go,
        normalize_advantages=args.normalize_advantages,
        baseline_learning_rate=args.baseline_learning_rate,
        baseline_gradient_steps=args.baseline_gradient_steps,
        gae_lambda=args.gae_lambda,
    )

    total_envsteps = 0
    # start_time = time.time()

    results_list = []

    # Run for several episodes
    for episode in range(args.num_episodes):
        trajs, envsteps_this_batch = utils.sample_trajectories(env=env,
                                                               policy=agent.actor, 
                                                               min_timesteps_per_batch=args.batch_size, 
                                                               max_length=max_ep_len)
        
        # trajs should be a list of dictionaries of NumPy arrays, where each dictionary corresponds to a trajectory.
        # this line converts this into a single dictionary of lists of NumPy arrays.        
        trajs_dict = {k: [traj[k] for traj in trajs] for k in trajs[0]}
        
        train_info: dict = agent.update(
            trajs_dict["observation"],
            trajs_dict["action"],
            trajs_dict["reward"],
            trajs_dict["terminal"]
        )

        # If the current iteration is a multiple of args.scalar_log_freq, it collects data for evaluation by sampling trajectories using the agent's actor policy.
        if episode % args.scalar_log_freq == 0:
            # save eval metrics
            print("\nCollecting data for eval...")
            eval_trajs, eval_envsteps_this_batch = utils.sample_trajectories(
                env, agent.actor, args.eval_batch_size, max_ep_len
            )

            logs = utils.compute_metrics(trajs, eval_trajs)

            results_list.append(utils.metrics_to_dict(trajs, eval_trajs, total_envsteps, train_info)) 

    # Save the results.
    # TODO: Implement this       

def main():
    import argparse

    parser = argparse.ArgumentParser()
    # parser.add_argument("--env_name", type=str, required=True)
    # parser.add_argument("--exp_name", type=str, required=True)
    parser.add_argument("--n_iter", "-n", type=int, default=200)

    parser.add_argument("--use_reward_to_go", "-rtg", action="store_true")
    parser.add_argument("--use_baseline", action="store_true")
    parser.add_argument("--baseline_learning_rate", "-blr", type=float, default=5e-3)
    parser.add_argument("--baseline_gradient_steps", "-bgs", type=int, default=5)
    parser.add_argument("--gae_lambda", type=float, default=None)
    parser.add_argument("--normalize_advantages", "-na", action="store_true")
    parser.add_argument(
        "--batch_size", "-b", type=int, default=1000
    )  # steps collected per train iteration
    parser.add_argument(
        "--eval_batch_size", "-eb", type=int, default=400
    )  # steps collected per eval iteration

    parser.add_argument("--discount", type=float, default=1.0)
    parser.add_argument("--learning_rate", "-lr", type=float, default=5e-3)
    parser.add_argument("--n_layers", "-l", type=int, default=2)
    parser.add_argument("--layer_size", "-s", type=int, default=64)

    parser.add_argument( "--ep_len", type=int)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--no_gpu", "-ngpu", action="store_true")
    parser.add_argument("--which_gpu", "-gpu_id", default=0)
    parser.add_argument("--video_log_freq", type=int, default=-1)
    parser.add_argument("--scalar_log_freq", type=int, default=1)

    parser.add_argument("--action_noise_std", type=float, default=0)

    args = parser.parse_args()

    run_training_loop(args)
    
if __name__ == "__main__":
    main()