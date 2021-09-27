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
