from collections import OrderedDict
import numpy as np
import copy
from environments.vertisim_env import VertiSimEnv
import os
import pickle
from typing import Dict, Tuple, List
from networks.policies import MLPPolicy

def sample_trajectory(
    env: VertiSimEnv, policy: MLPPolicy, max_length: int) -> Dict[str, np.ndarray]:
    """Sample a rollout in the environment from a policy."""
    ob = env.reset()
    obs, acs, rewards, next_obs, terminals = [], [], [], [], []
    steps = 0
    while True:
        # Use the most recent ob and the policy to decide what to do
        ac: np.ndarray = policy.get_action(ob)

        # Use that action to take a step in the environment
        next_ob, rew, done = env.step(ac)

        # Rollout can end due to done, or due to max_length
        steps += 1
        rollout_done: bool = int(done or steps >= max_length)

        # record result of taking that action
        obs.append(ob)
        acs.append(ac)
        rewards.append(rew)
        next_obs.append(next_ob)
        terminals.append(rollout_done)

        ob = next_ob  # jump to next timestep

        # end the rollout if the rollout ended
        if rollout_done:
            break

    return {
        "observation": np.array(obs, dtype=np.float32),
        "reward": np.array(rewards, dtype=np.float32),
        "action": np.array(acs, dtype=np.float32),
        "next_observation": np.array(next_obs, dtype=np.float32),
        "terminal": np.array(terminals, dtype=np.float32),
    }


def sample_trajectories(
    env: VertiSimEnv,
    policy: MLPPolicy,
    min_timesteps_per_batch: int,
    max_length: int,
    render: bool = False,
) -> Tuple[List[Dict[str, np.ndarray]], int]:
    """Collect rollouts using policy until we have collected min_timesteps_per_batch steps."""
    timesteps_this_batch = 0
    trajs = []
    while timesteps_this_batch < min_timesteps_per_batch:
        # collect rollout
        traj = sample_trajectory(env, policy, max_length, render)
        trajs.append(traj)

        # count steps
        timesteps_this_batch += get_traj_length(traj)
    return trajs, timesteps_this_batch


def get_traj_length(traj):
    return len(traj["reward"])