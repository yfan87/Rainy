import os
from rainy import Config, net
from rainy.agent import A2cAgent
from rainy.envs import Atari
import rainy.util.cli as cli
from rainy.envs import MultiProcEnv
from torch.optim import RMSprop


def config() -> Config:
    c = Config()
    c.set_env(lambda: Atari('Breakout'))
    c.set_optimizer(
        lambda params: RMSprop(params, lr=1e-4, alpha=0.99, eps=1e-5)
    )
    c.set_net_fn('actor-critic', net.actor_critic.ac_conv)
    c.num_workers = 16
    c.set_parallel_env(lambda env_gen, num_w: MultiProcEnv(env_gen, num_w))
    c.grad_clip = 5.0
    c.gae_tau = 1.0
    c.use_gae = False
    c.max_steps = int(2e7)
    c.eval_env = Atari('Breakout', episode_life=False)
    c.eval_freq = None
    return c


if __name__ == '__main__':
    cli.run_cli(config(), lambda c: A2cAgent(c), script_path=os.path.realpath(__file__))