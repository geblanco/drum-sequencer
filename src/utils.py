from enum import Enum


class ImmutableDict(dict):
    def __hash__(self):
        return id(self)

    def _immutable(self, *args, **kws):
        raise TypeError('object is immutable')

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear       = _immutable  # noqa: E221
    update      = _immutable  # noqa: E221
    setdefault  = _immutable  # noqa: E221
    pop         = _immutable  # noqa: E221
    popitem     = _immutable  # noqa: E221


def serialize_dict(config_dict):
    config = config_dict.copy()
    for key, value in config.items():
        if isinstance(value, Enum):
            config[key] = value.value
        elif isinstance(value, dict):
            for subk, subv in value.items():
                if isinstance(subv, Enum):
                    config[key][subk] = subv.value

    return config
