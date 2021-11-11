import mido

from .base import View
from track import Track
from modes import TrackMode
from track_control import TrackController


class TrackSelect(View):
    def __init__(
        self,
        track_controller,
        tracks_selector,
    ):
        self.track_controller = track_controller
        self.select_tracks = tracks_selector

    def __call__(self, note, value):
        if self.track_controller.is_track_select(note):
            selected = self.track_controller.toggle_selected_tracks(note)
            if len(selected):
                self.select_tracks(selected)

    def filter(self, note, value):
        return self.track_controller.is_track_select(note)
