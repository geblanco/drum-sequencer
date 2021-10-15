from enum import Enum


"""
The most probable mode is:
* toggle, handled, select-tracks
"""


class NoteMode(Enum):
    """Note Modes
    * Default: A note-on triggers the pad, a note-off triggers it off
    * Toggle: A note-on toggles the pad state from on/off and viceversa
    """
    default = "default"
    toggle = "toggle"


class LedMode(Enum):
    """Led Modes
    * handled: a note-on should be sent to the controller to let it lit
    * partially-handled: note-on is not sent, the controller itself gets lit,
        a note-off is sent to get light the pad off.
    * unhandled: the controller knows when it should be lit and not
    """
    handled = "handled"
    partial_handled = "partial_handled"
    unhandled = "unhandled"


class LedColors(Enum):
    default = None
    velocity = True


class TrackMode(Enum):
    """Track modes
    * Select-tracks: Only one track at a time is displayed.
    * All-tracks: All tracks are displayed at the same time (big controller or
        few tracks)
    """
    select_tracks = "select_tracks"
    all_tracks = "all_tracks"


class TrackSelectMode(Enum):
    arrows = "arrows"
    select = "select"


class ClockSource(Enum):
    controller = "controller"
    external = "external"
    internal = "internal"


class InputMode(Enum):
    """
    Controller can be set to different modes:

    sequencer:   The standard mode to sequence steps
    one_shot:    Just like a maschine, trigger a sound for each pad.
                 In the future, track select pads can be multipliers,
                 to repeat each sound on a 1/2, 1/4, 1/8, 1/16 fashion
    velocities:  Select velocity for each track. In the future a humanize
                 button could be added
    """
    sequencer = 0
    one_shot = 1
    velocities = 2


class DisplayMsgTypes(Enum):
    clock = "clock"
    track = "track"
