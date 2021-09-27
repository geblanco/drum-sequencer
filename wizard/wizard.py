import mido
import time

from math import floor
from prompts import query_num, query_choices, query_yn, confirm_pad
from modes import TrackMode, NoteMode
from rtmidi.midiutil import open_midiinput, open_midioutput


_HELP_STR_ = """
This wizard will help you configure your controller. It will guide you through
the process step by step, if any of the requested options is not clear, you
can hit `h` in any of the prompts to get this message again.

The wizard will do it's best to guess your setup, but it may fail, you can
always complete or fix your configuration in the `user_config.yaml` file.

This is an Open Source initiative, if you created a nice setup for your
controller, please share it at: # ToDo := share url. Thanks! (:

You can always exit the wizard by hitting Ctrl-c

Options:
------------------------------------------------------------------------------
* Number of tracks
------------------------------------------------------------------------------
This is the number of tracks you want the sequencer to handle. Typically, any
number between 1 and 8 tracks.

------------------------------------------------------------------------------
* Number of steps per track
------------------------------------------------------------------------------
This is the number of subdivisions per bar. Quarter note (1/4 = 4), half note
(1/2 = 2) and so on.

------------------------------------------------------------------------------
* Track Mode
------------------------------------------------------------------------------
This option has to do with your controller, options are `all_tracks`,
`select_tracks`, choose the first one if your controller can display all the
`number of tracks` at once. If your controller cannot handle all tracks at
once (either) too small controller or too much tracks for the controller, you
will have to choose the amount of displayed tracks and some buttons to toggle
between one track and another inside the controller.

------------------------------------------------------------------------------
* Number of displayed tracks
------------------------------------------------------------------------------
The number of tracks your controller can display at once.

------------------------------------------------------------------------------
* Select track mode
------------------------------------------------------------------------------
Arrows mode:  With two pads you roll between displayed tracks contiguously
Select track: You use one button to select each track (your controller must
              have one free button for each track).

------------------------------------------------------------------------------
* Track selection pads
------------------------------------------------------------------------------
Buttons to select the displayed tracks. Works with `select track mode` mode
to handle how tracks will be selected.
"""


def channel_and_note_mode(waiter):
    text = f"Press any pad on the controller"
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
    if not confirm_pad(text, waiter.midiout, query_pad.bytes()):
        raise RuntimeError(
            "Unknown inputs for your controller, check the manual for further"
            " information! This probably means that your controller "
        )
    
    output_channel = query_pad.channel
    return input_channel, output_channel, note_mode


def setup_controller(midiin, midiout):
    # Setup:
    #  - nof tracks
    #  - nof steps
    #  - track mode: select tracks, all_tracks, nof display tracks
    #  - for each displayed track, midiin, midiout, ledout
    #    midiout (can default to gmd spec)
    
    nof_tracks = query_num("Number of tracks?", int, sample=list(range(8)))
    nof_steps = query_num("Number of steps per track?", int, sample=[8, 16])
    if nof_steps < 8:
        raise ValueError(
            "Less than 8 steps? Is this a joke?"
        )

    track_choices = [en.value for en in TrackMode]
    nof_displayed_tracks = query_num(
        "How many tracks your controller displays at once?",
        type_=int, sample=list(range(8))
    )
    if nof_displayed_tracks < nof_tracks:
        track_mode = query_choices("Track Mode?", choices=track_choices)
        if track_mode == "a":
            track_mode = TrackMode.all_tracks
        else:
            track_mode = TrackMode.select_tracks
    else:
        track_mode = TrackMode.all_tracks

    track_select_mode = query_choices(
        "Select track mode?",
        choices=[en.value for en in TrackSelectMode]
    )
    if track_select_mode == TrackSelectMode.arrows:
        nof_select_pads = 2
    else:
        raw_select = nof_tracks/nof_displayed_tracks
        if raw_select > floor(raw_select):
            raw_select += 1
        nof_select_pads = int(raw_select)

    guesser = Guesser(midiin, midiout)
    i_channel, o_channel, note_mode = channel_and_note_mode(guesser.waiter)
    text = "Output MIDI channel for the Sequencer?"
    sequencer_channel = query_num(text, int, sample=list(range(1, 16 + 1)))

    print("Track selection pads")
    track_select_pads = guesser.guess_one_track(amount=nof_select_pads, step=1)
    note_input_track_map_1 = guesser.guess_one_track(amount=nof_steps, step=4)
    note_input_map = guesser.guess_tracks(
        note_input_track_map_1, amount=nof_displayed_tracks
    )

    return dict(
        note_mode=str(note_mode),
        track_mode=str(track_mode),
        input_channel=i_channel,
        output_channel=sequencer_channel,
        led_channel=o_channel,
        nof_tracks=nof_tracks,
        steps_per_track=nof_steps,
        note_input_map=note_input_map,
        track_select_map=track_select_pads,
    )