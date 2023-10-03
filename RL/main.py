import gymnasium as gym
import utils
import numpy as np
import torch
from utils import pytorch_util as ptu
from agents.pg_agent import PGAgent
import time

if __name__ == "__main__":

    # TODO: Implement this
    args = None

    # TODO: Implement this
    logger = Logger(args.logdir)

    # TODO: Implement this
    # set random seeds
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    ptu.init_gpu(use_gpu=not args.no_gpu, gpu_id=args.which_gpu)    

    # Create the environment
    config_file_path = args.config_file_path  # Point this to your actual config file path
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
    start_time = time.time()

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