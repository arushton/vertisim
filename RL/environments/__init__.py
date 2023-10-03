from gymnasium.envs.registration import register

register(
    id='VertiSim',
    entry_point='gymnasium.envs:VertiSimEnv',
    max_episode_steps=1000
    # reward_threshold=0.0,
    # nondeterministic=True,
)