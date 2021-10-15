from modes import TrackSelectMode


class TrackController(object):
    def __init__(self, config, display):
        self.config = config
        self.display = display

        self.nof_tracks = config["nof_tracks"]
        self.nof_steps = config["nof_steps"]
        self.nof_displayed_tracks = self.config["nof_displayed_tracks"]
        self.track_mode = config["track_mode"]
        self.track_select_map = config.get("track_select_map", [])
        self.track_select_mode = config["track_select_mode"]
        self.note_input_map = config["note_input_map"]

    def _is_select_up(self, note):
        return note == self.track_select_map[0]

    def _is_select_down(self, note):
        return note == self.track_select_map[1]

    def get_selected_tracks(self, note):
        select_ids = []
        if self.track_select_mode == TrackSelectMode.select:
            # direct track selection through button
            track_id = self.track_select_map.index(note)
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
