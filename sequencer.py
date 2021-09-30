import math
import mido

from track import Track
from modes import TrackMode, TrackSelectMode


# ToDo :=
# - maps: track_select (in TrackMode.select_tracks) note in, note out
#   track select map maps note to track
#   - should be propagated
#   note_in map are notes mapped to steps
#   - input note, output led
#   note_out map are notes mapped to tracks, each track emmits only on a note
#   - track -> output note
# - think about outputs
# config contains:
# - output_channel
# - nof_tracks
# - nof_steps
# - note_input_map
# - note_mode
# - track_mode
# - track_select_map
# - track_select_mode
# - nof_displayed_tracks
# - led_channel
# - led_colors
class Sequencer(object):
    def __init__(
        self,
        config,
        output_queue=None,
        led_queue=None,
    ):
        self.config = config
        self.track_mode = config["track_mode"]
        self.output_channel = config["output_channel"]
        self.nof_tracks = config["nof_tracks"]
        self.nof_steps = config["nof_steps"]
        self.track_select_map = config.get("track_select_map", [])
        self.track_select_mode = config["track_select_mode"]
        self.note_input_map = config["note_input_map"]
        self.note_output_map = config["note_output_map"]

        self.output_queue = output_queue

        self._current_beat = 0
        self._setup_tracks(led_queue)

        if (
            self.track_mode != TrackMode.all_tracks and
            (
                self.track_select_map is None or
                len(self.track_select_map) == 0
            ) and
            (self.nof_tracks * self.nof_steps) > len(self.note_input_map)
        ):
            raise ValueError(
                "You must choose track selection values to work with multiple"
                f" tracks in {self.track_mode} mode!"
            )

    def _setup_tracks(self, led_queue):
        self.tracks = []
        for track_id in range(self.nof_tracks):
            if self.track_mode == TrackMode.all_tracks:
                start = track_id * self.nof_steps
                end = (track_id * self.nof_steps + self.nof_steps)
            else:
                start = 0
                end = self.nof_steps

            if self.track_select_mode == TrackMode.all_tracks:
                select = True
            elif track_id < self.config["nof_displayed_tracks"]:
                select = True
            else:
                select = False

            # ToDo := notes map
            track = Track(
                track_id=track_id,
                config=self.config,
                note_input_map=self.note_input_map[start:end],
                led_queue=led_queue,
                select=select,
            )
            self.tracks.append(track)

    def _get_midimsgs_from_tracks(self):
        msgs = []
        tracks = [tr for tr in self.tracks if tr.solo or not tr.mute]
        steps = [tr.get_state()[self._current_beat] for tr in tracks]
        steps = [st for st in steps if st > 0]
        for track_id, step_val in enumerate(steps):
            track_msg = mido.Message(
                type="note_on",
                note=self.note_output_map[track_id],
                velocity=step_val,
                channel=self.output_channel
            )
            msgs.append(track_msg.bytes())
        return msgs

    def _track_id_from_note_map(self, note):
        track_id = self.note_input_map.index(note)
        track_id = math.floor(track_id / self.nof_steps)
        return track_id

    def _is_select_up(self, note):
        return note == self.track_select_map[0]

    def _is_select_down(self, note):
        return note == self.track_select_map[1]

    def _selected_tracks(self):
        return [tr for tr in self.tracks if tr.select]

    def _select_single_track(self, track_id):
        self._select_tracks([track_id])

    def _select_tracks(self, track_ids):
        unselect = [
            id for id in range(len(self.tracks)) if id not in track_ids
        ]
        for idx in unselect:
            self.tracks[idx].select = False

        for idx in track_ids:
            self.tracks[idx].select = True

    def _toggle_select_track(self, note):
        if self.track_select_mode == TrackSelectMode.select:
            # direct track selection through button
            track_id = self.track_select_map.index(note)
            self._select_single_track(track_id)
        else:
            # up/down arrows
            dir = None
            selected = self._selected_tracks()
            if (
                self._is_select_up(note) and
                selected[0].track_id > self.tracks[0].track_id
            ):
                dir = -1
            elif (
                self._is_select_down(note) and
                selected[-1].track_id < self.tracks[-1].track_id
            ):
                dir = 1

            if dir is not None:
                ids = [tr.track_id + dir for tr in selected]
                self._select_tracks(ids)

    # Process track events
    def process(self, message):
        is_note_message = False
        if message.type in ["note_on", "note_off"]:
            note = message.note
            is_note_message = True
        elif message.type in ["control_change"]:
            note = message.control

        if note in self.track_select_map:
            if self.track_mode == TrackMode.select_tracks:
                self._toggle_select_track(note)
        elif note in self.note_input_map:
            target_track_id = self._track_id_from_note_map(note)
            if not is_note_message:
                type_ = "note_on" if note > 0 else "note_off"
                message = mido.Message(
                    type=type_,
                    note=note,
                    velocity=message.value
                )

            self.tracks[target_track_id](message)

    # Step the sequencer
    def tick(self):
        print("tick")
        msgs = self._get_midimsgs_from_tracks()
        self.output_queue.put(msgs)
        self._current_beat = (self._current_beat + 1) % self.nof_steps

    def start(self):
        self._current_beat = 0

    def stop(self):
        self._current_beat = 0
