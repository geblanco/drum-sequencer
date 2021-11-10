import math

from utils import ButtonToggler
from modes import TrackSelectMode, TrackMode


class TrackController(object):
    def __init__(self, config, display):
        self.config = config
        self.display = display

        self.nof_steps = config["nof_steps"]
        self.nof_displayed_tracks = self.config["nof_displayed_tracks"]
        self.track_mode = config["track_mode"]
        self.track_controls_map = config.get(
            "track_controls_map", dict(solo=[], mute=[])
        )
        self.track_select_mode = config["track_select_mode"]
        self.note_input_map = config["note_input_map"]
        self.led_output_map = config["led_config"].get(
            "led_output_map", config["note_input_map"]
        )
        self.track_selector = ButtonToggler(
            sel_mode=self.track_select_mode,
            sel_map=config.get("track_select_map", []),
            nof_displayed_opts=self.nof_displayed_tracks,
            max_opts=config["nof_tracks"],
            update_hook=self.update_display_index
        )

    def update_display_index(self, value):
        self.display.display_index = value

    def is_track_select(self, note):
        return self.track_selector.should_toggle(note)

    def is_track_control(self, note):
        return (
            note in self.track_controls_map["solo"] or
            note in self.track_controls_map["mute"]
        )

    def toggle_selected_tracks(self, note):
        return self.track_selector.toggle(note)

    def get_target_track(self, note):
        track_id = self.note_input_map.index(note)
        track_id = math.floor(track_id / self.nof_steps)
        return track_id + self.display.display_index

    def get_control_target_note(self, track_id, control):
        target = self.track_controls_map["solo"]
        if control == "mute":
            target = self.track_controls_map["mute"]

        index = track_id - self.display.display_index
        if index < 0 or index > len(target):
            raise RuntimeError(
                "Requested a note out of range!"
                f"Processed index: {index}, max: {len(target)}"
            )

        return target[index]

    def get_control_target_track(self, note):
        select_id = None
        control_type_str = None

        if note in self.track_controls_map["solo"]:
            select_id = self.track_controls_map["solo"].index(note)
            control_type_str = "solo"
        else:
            select_id = self.track_controls_map["mute"].index(note)
            control_type_str = "mute"

        if self.track_select_mode == TrackSelectMode.select:
            select_id = self.display.display_index
        else:
            select_id += self.display.display_index

        return {control_type_str: select_id}

    def get_track_step_note(self, track_id, step_id):
        multitrack = (
            self.track_mode == TrackMode.all_tracks or
            self.nof_displayed_tracks > 1
        )
        if multitrack:
            start = (track_id - self.display.display_index) * self.nof_steps
            end = (track_id - self.display.display_index) * \
                self.nof_steps + self.nof_steps
        else:
            start = 0
            end = self.nof_steps

        end_note = self.led_output_map[start:end][step_id]
        return end_note
