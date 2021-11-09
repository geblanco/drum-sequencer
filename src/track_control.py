import math

from modes import TrackSelectMode, TrackMode


class TrackController(object):
    def __init__(self, config, display):
        self.config = config
        self.display = display

        self.nof_tracks = config["nof_tracks"]
        self.nof_steps = config["nof_steps"]
        self.nof_displayed_tracks = self.config["nof_displayed_tracks"]
        self.track_mode = config["track_mode"]
        self.track_select_map = config.get("track_select_map", [])
        self.track_controls_map = config.get(
            "track_controls_map", dict(solo=[], mute=[])
        )
        self.track_select_mode = config["track_select_mode"]
        self.note_input_map = config["note_input_map"]
        self.led_output_map = config["led_config"].get(
            "led_output_map", config["note_input_map"]
        )

    def _is_select_up(self, note):
        return note == self.track_select_map[0]

    def _is_select_down(self, note):
        return note == self.track_select_map[1]

    def is_track_select(self, note):
        return note in self.track_select_map

    def is_track_control(self, note):
        return (
            note in self.track_controls_map["solo"] or
            note in self.track_controls_map["mute"]
        )

    def get_selected_tracks(self, note):
        select_ids = []
        if self.track_select_mode == TrackSelectMode.select:
            # direct track selection through button
            track_id = self.track_select_map.index(note)
            self.display.display_index = track_id
            select_ids.append(track_id)
        else:
            # up/down arrows
            dir = -1 if self._is_select_up(note) else 1
            display_index = self.display.display_index
            prev_display = display_index
            display_index += dir
            display_index = min(
                max(display_index, 0),
                self.nof_tracks - self.nof_displayed_tracks
            )
            self.display.display_index = display_index
            if prev_display != display_index:
                for track_id in range(self.nof_displayed_tracks):
                    target_track_id = track_id + display_index
                    select_ids.append(target_track_id)

        return select_ids

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
            end = (
                (track_id - self.display.display_index) *
                self.nof_steps + self.nof_steps
            )
        else:
            start = 0
            end = self.nof_steps

        end_note = self.led_output_map[start:end][step_id]
        return end_note
