from functools import partial
from typing import Callable, Iterable, Optional, Union
from torch import nn, Tensor

# function to init Tensor
InitFn = Callable[[Tensor], None]


def uniform(mean: float=0., var: float=1.) -> InitFn:
    return partial(nn.init.uniform_, a=mean, b=var)


def orthogonal(gain: float=1.) -> InitFn:
    return partial(nn.init.orthogonal_, gain=gain)


def constant(val: float) -> InitFn:
    return partial(nn.init.constant_, val=val)


def zero() -> InitFn:
    return partial(nn.init.constant_, val=0)


class Initializer:
    """Utility Class to initialize weight parameters of NN
    """
    def __init__(
            self,
            nonlinearity: Optional[str] = None,
            weight_init: InitFn = orthogonal(),
            bias_init: InitFn = zero(),
            scale: float = 1.,
    ) -> None:
        """If nonlinearity is specified, use orthogonal with
           with calucurated gain by torch.init.calculate_gain.
        """
        if nonlinearity:
            gain = nn.init.calculate_gain(nonlinearity)
            self.weight_init = orthogonal(gain)
        else:
            self.weight_init = weight_init
        self.bias_init = bias_init
        self.scale = scale

    def __call__(self, mod: Union[nn.Module, nn.Sequential, Iterable[nn.Module]]) -> nn.Module:
        if hasattr(mod, '__iter__'):
            self.__init_list(mod)
        elif isinstance(mod, nn.Sequential):
            self.__init_seq(mod)
        else:
            self.__init_mod(mod)
        return mod

    def make_list(self, *args) -> nn.ModuleList:
        return nn.ModuleList([self.__init_mod(mod) for mod in args])

    def make_seq(self, *args) -> nn.Sequential:
        return nn.Sequential(*map(lambda mod: self.__init_mod(mod), args))

    def __init_mod(self, mod: nn.Module) -> nn.Module:
        self.weight_init(mod.weight.data)
        self.bias_init(mod.bias.data)
        mod.weight.data.mul_(self.scale)
        return mod

    def __init_list(self, mods: Iterable[nn.Module]) -> Iterable[nn.Module]:
        for mod in mods:
            self.__init_mod(mod)
        return mods

    def __init_seq(self, seq: nn.Sequential) -> nn.Sequential:
        for mod in seq._modules.values():
            self.__init_mod(mod)
        return seq


