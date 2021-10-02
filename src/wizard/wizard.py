# noqa: E402

import sys
import yaml
import time
import mido

from enum import Enum
from math import floor

sys.path.append("..")
from controller import (  # noqa: E402
    flush_controller,
    open_controller,
    search_controller_config,
)
from guesser import Guesser  # noqa: E402
from modes import (  # noqa: E402
    TrackMode,
    TrackSelectMode,
    NoteMode,
    LedColors,
)
from prompts import (  # noqa: E402
    query_num,
    query_choices,
    query_yn,
    confirm_pad,
    _HELP_STR_,
)


sequencer_keys = [
    "output_channel",
    "nof_displayed_tracks",
    "nof_tracks",
    "nof_steps",
]

track_modes = [
    "track_mode",
    "track_select_mode",
]


def channel_and_note_mode(waiter):
    flush_controller(waiter.midiout)
    print("Press any pad on the controller")
    query_pad = waiter.wait_for_key()
    input_channel = query_pad.channel
    note_mode = NoteMode.default
    if not query_yn("Is the pad still on?"):
        note_mode = NoteMode.toggle

    text = "Does this light the same button?"
    if not confirm_pad(text, waiter.midiout, query_pad):
        raise RuntimeError(
            "Unknown inputs for your controller, check the manual for further"
            " information! This probably means that your controller "
        )

    return input_channel, note_mode


def multi_color_check(waiter):
    flush_controller(waiter.midiout)
    led_color_mode = LedColors.default
    print("Velocity controlled colors. Press any key on the controller")
    query_pad = waiter.wait_for_key()
    query_pad.velocity = 64
    waiter.midiout.send_message(query_pad.bytes())
    if query_yn("Is the pad on?"):
        query_pad.velocity = (query_pad.velocity + 50) % 127
        waiter.midiout.send_message(query_pad.bytes())
        if query_yn("Has it changed its color?"):
            led_color_mode = LedColors.velocity

    return led_color_mode


def generate_track_velocities(nof_tracks):
    start_incr = 127 // nof_tracks
    velocities = list(range(start_incr, 127, start_incr))
    return velocities


def display_track(midiout, notes, nof_steps, led_color_mode):
    # light off
    for note in notes:
        if note > 127:
            raise ValueError("note out", notes)
        message = mido.Message(type="note_off", note=note, velocity=0)
        midiout.send_message(message.bytes())

    nof_tracks = len(notes) // nof_steps
    velocities = [127] * nof_tracks
    if led_color_mode == LedColors.velocity:
        velocities = generate_track_velocities(nof_tracks)

    for id, note in enumerate(notes):
        message = mido.Message(
            type="note_on", note=note, velocity=velocities[id // nof_steps]
        )
        midiout.send_message(message.bytes())
        if ((id + 1) % 16) == 0:
            time.sleep(0.5)


def get_num_select_pads(config):
    if config["track_select_mode"] == TrackSelectMode.arrows:
        nof_select_pads = 2
    else:
        raw_select = config["nof_tracks"] / config["nof_displayed_tracks"]
        if raw_select > floor(raw_select):
            raw_select += 1
        nof_select_pads = int(raw_select)

    return nof_select_pads


def setup_sequencer():
    print("\n=================== Sequencer Config ===================")
    # Setup:
    #  - nof tracks
    #  - nof steps
    #  - track mode: select tracks, all_tracks, nof display tracks
    nof_tracks = query_num(
        "Number of tracks?",
        type_=int,
        sample=list(range(1, 8)),
        constraints=[1, 32]
    )
    nof_steps = query_num(
        "Number of steps per track?",
        type_=int,
        sample=list(range(4, 32, 4)),
        constraints=[8, 64]
    )
    nof_displayed_tracks = query_num(
        "How many tracks your controller displays at once?",
        type_=int,
        sample=list(range(1, 8)),
        constraints=[1, 32]
    )

    text = "Output MIDI channel for the Sequencer?"
    sequencer_channel = query_num(
        text,
        type_=int,
        sample=list(range(1, 16 + 1)),
        constraints=[1, 16]
    )
    # account for 0ed index
    sequencer_channel -= 1

    return dict(
        output_channel=sequencer_channel,
        nof_displayed_tracks=nof_displayed_tracks,
        nof_tracks=nof_tracks,
        nof_steps=nof_steps,
    )


def setup_track_modes(config):
    nof_tracks = config["nof_tracks"]
    nof_displayed_tracks = config["nof_displayed_tracks"]
    track_mode = TrackMode.all_tracks
    track_select_mode = TrackSelectMode.arrows

    if nof_displayed_tracks < nof_tracks:
        print("\n=================== Track Config =======================")
        track_select_mode = query_choices(
            "Select track mode",
            choices=[en.value for en in TrackSelectMode]
        )
        if track_select_mode == "a":
            track_select_mode = TrackSelectMode.arrows
        else:
            track_select_mode = TrackSelectMode.select

        track_mode = TrackMode.select_tracks

    return dict(
        track_mode=track_mode,
        track_select_mode=track_select_mode,
    )


def setup_controller(midiin, midiout, config):
    print("\n=================== Controller Config ==================")
    nof_steps = config["nof_steps"]
    nof_displayed_tracks = config["nof_displayed_tracks"]
    track_mode = config["track_mode"]
    nof_select_pads = get_num_select_pads(config)

    guesser = Guesser(midiin, midiout)
    io_keys = ["input_channel", "note_mode"]
    if any([config.get(key, None) is None for key in io_keys]):
        print("> Basics -----------------------------------------------")
        i_channel, note_mode = channel_and_note_mode(guesser.waiter)
    else:
        i_channel, note_mode = [config.get(key) for key in io_keys]

    if config.get("led_color_mode", None) is None:
        led_color_mode = multi_color_check(guesser.waiter)
    else:
        led_color_mode = LedColors(config.get("led_color_mode"))

    flush_controller(midiout)
    track_select_pads = None
    if track_mode == TrackMode.select_tracks:
        print("\n> Track selection pads ---------------------------------")
        track_select_pads = guesser.guess_select_track(amount=nof_select_pads)

    flush_controller(midiout)
    print("\n> Tracks config: First track ---------------------------")
    note_input_map = guesser.guess_one_track(nof_steps=nof_steps)
    display_track(midiout, note_input_map, nof_steps, LedColors.default)
    if nof_displayed_tracks > 1:
        print("\n> Tracks config: Rest of tracks-------------------------")
        new_map = guesser.guess_tracks(
            note_input_map[:16], nof_tracks=nof_displayed_tracks - 1
        )
        note_input_map.extend(new_map)

    return dict(
        note_mode=note_mode,
        input_channel=i_channel,
        note_input_map=note_input_map,
        track_select_map=track_select_pads,
        led_config=dict(
            led_channel=i_channel,
            led_color_mode=led_color_mode
        )
    )


def setup_velocities(config):
    ret = {}
    if config["led_config"]["led_color_mode"] == LedColors.velocity:
        velocities = generate_track_velocities(config["nof_tracks"])
        ret["led_colors"] = velocities

    return ret


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


def load_config(conf_path):
    config = {}
    if conf_path.exists():
        text = f"Found already existing config in {conf_path}. Load it?"
        if query_yn(text):
            config = yaml.safe_load(open(conf_path, "r"))

    return config


def main(overwrite=False):
    print(_HELP_STR_)
    print(
        "You will now be prompted to select MIDI I/O for your controller.\n"
        "Don't select to create virtual ports!"
    )

    ctrl = open_controller()
    midiin, midiout = ctrl["input_port"], ctrl["output_port"]
    portname = ctrl["input_name"]
    conf_path = search_controller_config(portname)
    config = load_config(conf_path)
    try:
        if any([config.get(key, None) is None for key in sequencer_keys]):
            config.update(**setup_sequencer())

        if any([config.get(key, None) is None for key in track_modes]):
            config.update(**setup_track_modes(config))

        flush_controller(midiout)
        config.update(**setup_controller(midiin, midiout, config))
        config["led_config"].update(**setup_velocities(config))
        config = serialize_dict(config)

        conf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(conf_path, "w") as fout:
            fout.write(yaml.dump(config))

        display_track(
            midiout,
            config["note_input_map"],
            config["nof_steps"],
            LedColors(config["led_config"]["led_color_mode"]),
        )
        if query_yn("Did the track correctly lit?"):
            print(
                "Great!!\nWe are finished, go on and create some music!\n"
                "Don't forget to share your config so other folks can use it!"
                "=)"
            )
        else:
            print("Sorry, something went wrong...")

        print(f"Your config is saved in {conf_path}")

    except Exception as ex:
        print(ex)
        raise ex


if __name__ == "__main__":
    main(overwrite=True)
