"""Algorithmics module — reusable quantum algorithm components."""

import importlib

__all__ = [
    "measurement",
    "state_preparation",
    "ansatz",
    "circuits",
]


def __getattr__(name):
    if name in __all__:
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + __all__)
