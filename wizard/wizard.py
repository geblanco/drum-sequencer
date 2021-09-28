import sys
import yaml
import time
import mido

sys.path.append("..")
from math import floor
from guesser import Guesser
from prompts import (
    query_num,
    query_choices,
    query_yn,
    confirm_pad,
    _HELP_STR_,
)
from modes import TrackMode, TrackSelectMode, NoteMode
from rtmidi.midiutil import open_midiinput, open_midioutput


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


def setup_controller(midiin, midiout):
    # Setup:
    #  - nof tracks
    #  - nof steps
    #  - track mode: select tracks, all_tracks, nof display tracks
    #  - for each displayed track, midiin, midiout, ledout
    #    midiout (can default to gmd spec)

    nof_tracks = query_num("Number of tracks?", int, sample=list(range(1, 8)))
    if nof_tracks < 1:
        raise ValueError(
            "Less than 1 track? Really?"
        )

    nof_steps = query_num(
        "Number of steps per track?", int, sample=list(range(4, 32, 4))
    )
    if nof_steps < 8:
        raise ValueError(
            "Less than 8 steps? Is this a joke?"
        )

    nof_displayed_tracks = query_num(
        "How many tracks your controller displays at once?",
        type_=int, sample=list(range(1, 8))
    )

    if nof_displayed_tracks < 1:
        raise ValueError(
            "Your controller cannot display any track? Seriously?"
        )

    text = "Output MIDI channel for the Sequencer?"
    sequencer_channel = query_num(text, int, sample=list(range(1, 16 + 1)))
    # account for 0ed index
    sequencer_channel -= 1

    guesser = Guesser(midiin, midiout)
    i_channel, o_channel, note_mode = channel_and_note_mode(guesser.waiter)

    track_mode = TrackMode.all_tracks
    track_select_mode = TrackSelectMode.arrows
    if nof_displayed_tracks < nof_tracks:
        track_select_mode = query_choices(
            "Select track mode",
            choices=[en.value for en in TrackSelectMode]
        )
        if track_select_mode == "a":
            track_select_mode = TrackSelectMode.arrows
            nof_select_pads = 2
        else:
            track_select_mode = TrackSelectMode.select
            raw_select = nof_tracks / nof_displayed_tracks
            if raw_select > floor(raw_select):
                raw_select += 1
            nof_select_pads = int(raw_select)

        track_mode = TrackMode.select_tracks

    track_select_pads = None
    if track_mode == TrackMode.select_tracks:
        print("Track selection pads")
        track_select_pads = guesser.guess_select_track(amount=nof_select_pads)

    note_input_map = guesser.guess_one_track(amount=nof_steps, step=4)
    if nof_displayed_tracks > 1:
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
        note_mode=str(note_mode),
        track_mode=str(track_mode),
        track_select_mode=str(track_select_mode),
        input_channel=i_channel,
        output_channel=sequencer_channel,
        led_channel=o_channel,
        nof_tracks=nof_tracks,
        steps_per_track=nof_steps,
        note_input_map=note_input_map,
        track_select_map=track_select_pads,
    )


def main(overwrite=False):
    midiin, in_portname = open_midiinput(interactive=True)
    midiout, out_portname = open_midioutput(interactive=True)
    flush_controller(midiout)
    try:
        conf = setup_controller(midiin, midiout)
        conf_name = in_portname.split(":")[0].lower().replace(" ", "_") + ".yaml"

        with open(conf_name, "w") as fout:
            fout.write(yaml.dump(conf))
    except Exception as ex:
        print(ex)
        raise ex


if __name__ == "__main__":
    main(overwrite=True)
