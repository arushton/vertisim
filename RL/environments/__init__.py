from gymnasium.envs.registration import register

register(
    id='VertiSim',
    entry_point='environments.vertisim_env:VertiSimEnv',
    max_episode_steps=100000
    # reward_threshold=0.0,
    # nondeterministic=True,
)