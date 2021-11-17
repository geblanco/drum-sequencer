import os
import yaml

from enum import Enum
from modes import SelectMode
from typing import Callable
from pathlib import Path
from modes import (
    TrackMode,
    TrackSelectMode,
    NoteMode,
    LedMode,
    LedColors,
)


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


class SliceSelector(object):
    def __init__(
        self,
        sel_mode,
        sel_map,
        nof_displayed_opts,
        max_opts,
        min_index=0,
        start_index=0,
        increment=1,
        update_hook=None,
    ):
        self.index = start_index
        self.sel_mode = sel_mode
        self.sel_map = sel_map
        self.nof_displayed_opts = nof_displayed_opts
        self.max_opts = max_opts
        self.min_index = min_index
        self.increment = increment
        self.update_hook = noop
        if isinstance(update_hook, Callable):
            self.update_hook = update_hook

    def _is_select_up(self, value):
        return value == self.sel_map[0]

    def _is_select_down(self, value):
        return value == self.sel_map[1]

    def should_toggle(self, value):
        return value in self.sel_map

    def toggle(self, value):
        selections = []
        if value in self.sel_map:
            if self.sel_mode == SelectMode.select:
                target = self.sel_map.index(value)
                self.index = target
                selections.append(target)
            else:
                # up/down arrows
                dir = (
                    -self.increment if self._is_select_up(value)
                    else self.increment
                )
                prev_display = self.index
                self.index += dir
                self.index = min(
                    max(self.index, self.min_index),
                    self.max_opts - self.nof_displayed_opts
                )
                if prev_display != self.index:
                    for target in range(self.nof_displayed_opts):
                        selections.append(target + self.index)

            self.update_hook(self.index)
        return selections

    def get_selected(self):
        selections = []
        if self.sel_mode == SelectMode.select:
            selections.append(self.index)
        else:
            for target in range(self.nof_displayed_opts):
                selections.append(target + self.index)

        return selections


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


def noop(*args, **kwargs):
    return None


def load_config(config_path):
    config = yaml.safe_load(open(config_path))
    print(f"Load config from {config_path}")
    enums = [
        ("note_mode", NoteMode),
        ("track_mode", TrackMode),
        ("track_select_mode", TrackSelectMode),
    ]
    for key, class_ in enums:
        config[key] = class_(config[key])

    # ToDo := I/O channels indexed in 1, 0
    config["led_config"]["led_mode"] = LedMode(
        config["led_config"].get("led_mode", LedMode.handled)
    )
    config["led_config"]["led_color_mode"] = LedColors(
        config["led_config"].get("led_color_mode", LedColors.default)
    )

    if config["led_config"].get("led_map_out", None) is None:
        config["led_config"]["led_map_out"] = config["note_input_map"]

    if config.get("note_output_map", None) is None:
        config["note_output_map"] = [
            36 + i for i in range(config["nof_tracks"])
        ]

    if config.get("drumpad_output_map", None) is None:
        nof_drumpads = min(len(config["note_input_map"]), 16)
        config["drumpad_output_map"] = [
            36 + i for i in range(nof_drumpads)
        ]

    config["all_track_controls"] = config.get("track_select_map").copy()
    if config.get("track_controls_map", None) is not None:
        solos = config.get("track_controls_map")["solo"].copy()
        mutes = config.get("track_controls_map")["mute"].copy()
        config["all_track_controls"].extend([*solos, *mutes])

    return ImmutableDict(config)


def load_programmers(config_path):
    programmers = {}
    programmer_name = os.path.dirname(config_path)
    programmers_file = Path(programmer_name).joinpath("programmers.yaml")
    if programmers_file.exists():
        programmers = yaml.safe_load(open(programmers_file))
        print(f"Load programmers file from {programmers_file}")

    return programmers


def save_controller_ports(ctrl, config_path):
    config = yaml.safe_load(open(config_path))
    config["controller_input_port"] = ctrl["input_name"]
    config["controller_output_port"] = ctrl["output_name"]
    config = serialize_dict(config)
    with open(config_path, "w") as fout:
        fout.write(yaml.dump(config))
