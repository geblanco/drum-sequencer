from modes import ViewMode

from .base import View


class ClockOffset(View):
    view_mode = ViewMode.omni

    def __init__(
        self,
        config,
        clock_controller,
    ):
        self.note_map = config["clock_offset_map"]
        self.clock_controller = clock_controller

    def __call__(self, note, value):
        direction = -1 if self.note_map.index(note) == 0 else 1
        self.clock_controller.one_shot_offset(direction=direction)

    def filter(self, note, value):
        return note in self.note_map
