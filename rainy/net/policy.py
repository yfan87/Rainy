from abc import ABC, abstractmethod
from torch import nn, Tensor
from torch.distributions import Bernoulli, Categorical, Distribution, Normal
from torch.nn import functional as F
from typing import Any, Optional
from ..prelude import Array, Self
from ..utils import Device


class Policy(ABC):
    def __init__(self, dist: Distribution) -> None:
        self.dist = dist
        self._action: Optional[Tensor] = None

    def action(self) -> Tensor:
        if self._action is None:
            self._action = self.dist.sample().detach()
        return self._action.squeeze()

    def action_as_np(self) -> Array:
        return self.action().cpu().numpy()

    def set_action(self, action: Tensor) -> None:
        self._action = action

    @abstractmethod
    def __getitem__(self, idx: Any) -> Self:
        pass

    @abstractmethod
    def best_action(self) -> Tensor:
        pass

    @abstractmethod
    def log_prob(self) -> Tensor:
        pass

    @abstractmethod
    def entropy(self) -> Tensor:
        pass


class BernoulliPolicy(Policy):
    def best_action(self) -> Tensor:
        return self.dist.probs > 0.5

    def log_prob(self) -> Tensor:
        return self.dist.log_prob(self.action())

    def entropy(self) -> Tensor:
        return self.dist.entropy()

    def __getitem__(self, idx: Any) -> Tensor:
        return BernoulliPolicy(Bernoulli(logits=self.dist.logits[idx]))


class CategoricalPolicy(Policy):
    def best_action(self) -> Tensor:
        return self.dist.probs.argmax(dim=-1)

    def log_prob(self) -> Tensor:
        return self.dist.log_prob(self.action())

    def entropy(self) -> Tensor:
        return self.dist.entropy()

    def __getitem__(self, idx: Any) -> Self:
        return CategoricalPolicy(Categorical(logits=self.dist.logits[idx]))


class GaussianPolicy(Policy):
    def best_action(self) -> Tensor:
        return self.dist.mean

    def entropy(self) -> Tensor:
        return self.dist.entropy().sum(-1)

    def log_prob(self) -> Tensor:
        return self.dist.log_prob(self.action()).sum(-1)

    def __getitem__(self, idx: Any) -> Self:
        return GaussianPolicy(Normal(self.dist.mean[idx], self.dist.stddev[idx]))


class PolicyDist(ABC, nn.Module):
    def __init__(self, action_dim: int, *args, **kwargs) -> None:
        super().__init__()
        self.action_dim = action_dim

    @property
    def input_dim(self) -> int:
        return self.action_dim

    @abstractmethod
    def forward(self, t: Tensor) -> Policy:
        pass


class BernoulliDist(PolicyDist):
    """Bernoulli policy with no learnable parameter
    """
    def forward(self, x: Tensor) -> Policy:
        return BernoulliPolicy(Bernoulli(logits=x))


class CategoricalDist(PolicyDist):
    """Categorical policy with no learnable parameter
    """
    def forward(self, x: Tensor) -> Policy:
        return CategoricalPolicy(Categorical(logits=x))


class GaussinanDist(PolicyDist):
    """Gaussian policy which takes both mean and stdev as inputs
    """
    @property
    def input_dim(self) -> int:
        return self.action_dim * 2

    def forward(self, x: Tensor) -> Policy:
        size = x.size(1) // 2
        mean, stddev = x[:, :size], x[:, size:]
        return GaussianPolicy(Normal(mean, F.softplus(stddev)))


class SeparateStdGaussianDist(PolicyDist):
    """Gaussian policy which takes only mean as an input, and has a standard deviation
       independent with states, as a lernable parameter.
    """
    def __init__(self, action_dim: int, device: Device) -> None:
        super().__init__(action_dim)
        self.stddev = nn.Parameter(device.zeros(action_dim))

    def forward(self, x: Tensor) -> Policy:
        return GaussianPolicy(Normal(x, F.softplus(self.stddev)))
