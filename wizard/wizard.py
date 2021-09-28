# noqa: E402

import sys
import yaml
import time
import mido

from math import floor
from pathlib import Path
from rtmidi.midiutil import open_midiinput, open_midioutput

sys.path.append("..")
from guesser import Guesser  # noqa: E402
from modes import TrackMode, TrackSelectMode, NoteMode  # noqa: E402
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
    "steps_per_track",
]

track_modes = [
    "track_mode",
    "track_select_mode",
]


def channel_and_note_mode(waiter):
    print("Press any pad on the controller")
    query_pad = waiter.wait_for_key()
    input_channel = query_pad.channel
    if query_yn("Is the pad still on?"):
        note_mode = NoteMode.default
        query_pad.type = "note_off"
        query_pad.velocity = 0
        waiter.midiout.send_message(query_pad)
    else:
        note_mode = NoteMode.toggle

    text = "Does this light the same button?"
    if not confirm_pad(text, waiter.midiout, query_pad):
        raise RuntimeError(
            "Unknown inputs for your controller, check the manual for further"
            " information! This probably means that your controller "
        )

    output_channel = query_pad.channel
    return input_channel, output_channel, note_mode


def flush_controller(midiout):
    for i in range(127):
        message = mido.Message(type="note_off", note=i, velocity=0)
        midiout.send_message(message.bytes())


def display_track(midiout, notes):
    # light off
    for note in notes:
        if note > 127:
            raise ValueError("note out", notes)
        message = mido.Message(type="note_off", note=note, velocity=0)
        midiout.send_message(message.bytes())

    for note in notes:
        message = mido.Message(type="note_on", note=note, velocity=127)
        midiout.send_message(message.bytes())
        time.sleep(0.1)


def setup_sequencer():
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
        steps_per_track=nof_steps,
    )


def setup_track_modes(config):
    nof_tracks = config["nof_tracks"]
    nof_displayed_tracks = config["nof_displayed_tracks"]
    track_mode = TrackMode.all_tracks
    track_select_mode = TrackSelectMode.arrows

    if nof_displayed_tracks < nof_tracks:
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


def get_num_select_pads(config):
    if config["track_select_mode"] == TrackSelectMode.arrows:
        nof_select_pads = 2
    else:
        raw_select = config["nof_tracks"] / config["nof_displayed_tracks"]
        if raw_select > floor(raw_select):
            raw_select += 1
        nof_select_pads = int(raw_select)

    return nof_select_pads


def setup_controller(midiin, midiout, config):
    nof_steps = config["nof_steps"]
    nof_displayed_tracks = config["nof_displayed_tracks"]
    track_mode = config["track_mode"]
    track_select_mode = config["track_select_mode"]
    nof_select_pads = get_num_select_pads(config)

    print("> Basics -----------------------------------------------")
    guesser = Guesser(midiin, midiout)
    i_channel, o_channel, note_mode = channel_and_note_mode(guesser.waiter)

    track_select_pads = None
    if track_mode == TrackMode.select_tracks:
        print("> Track selection pads ---------------------------------")
        track_select_pads = guesser.guess_select_track(amount=nof_select_pads)

    print("> Tracks config: First track ---------------------------")
    note_input_map = guesser.guess_one_track(amount=nof_steps, step=4)
    if nof_displayed_tracks > 1:
        print("> Tracks config: Rest of tracks-------------------------")
        note_input_map.extend(guesser.guess_tracks(
            note_input_map, amount=nof_displayed_tracks - 1
        ))

    display_track(midiout, note_input_map)
    if query_yn("Did the track correctly lit?"):
        print(
            "Great!!\nWe are finished, go on and create some music!\n"
            "Don't forget to share your config so other folks can use it! (:"
        )
    else:
        print("Sorry, something went wrong...")

    return dict(
        **config,
        note_mode=str(note_mode),
        track_mode=str(track_mode),
        track_select_mode=str(track_select_mode),
        input_channel=i_channel,
        led_channel=o_channel,
        note_input_map=note_input_map,
        track_select_map=track_select_pads,
    )


def main(overwrite=False):
    print(_HELP_STR_)
    midiin, in_portname = open_midiinput(interactive=True)
    midiout, out_portname = open_midioutput(interactive=True)
    conf_name = in_portname.split(":")[0].lower().replace(" ", "_") + ".yaml"
    conf_path = Path("controllers").joinpath(conf_name)
    config = {}
    try:
        if conf_path.exists():
            text = f"Found already existing config in {conf_path}. Load it?"
            if query_yn(text):
                config = yaml.safe_load(open(conf_path, "r"))

        if any([config.get(key, None) is None for key in sequencer_keys]):
            print("=================== Sequencer Config ===================")
            config.update(**setup_sequencer())

        if any([config.get(key, None) is None for key in track_modes]):
            print("=================== Track Config =======================")
            config.update(**setup_track_modes(config))

        flush_controller(midiout)
        print("=================== Controller Config ==================")
        config = setup_controller(midiin, midiout, config)
        with open(conf_name, "w") as fout:
            fout.write(yaml.dump(config))
    except Exception as ex:
        print(ex)
        raise ex


if __name__ == "__main__":
    main(overwrite=True)
