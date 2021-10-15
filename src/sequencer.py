import mido

from track import Track
from modes import TrackMode
from track_control import TrackController


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
        display_queue,
        output_queue=None,
    ):
        self.config = config
        self.display = display_queue
        self.track_mode = config["track_mode"]
        self.output_channel = config["output_channel"]
        self.nof_tracks = config["nof_tracks"]
        self.nof_steps = config["nof_steps"]
        self.track_select_map = config.get("track_select_map", [])
        self.track_select_mode = config["track_select_mode"]
        self.note_input_map = config["note_input_map"]
        self.note_output_map = config["note_output_map"]

        self.track_controller = TrackController(config, display_queue)
        self.output_queue = output_queue

        self._current_beat = 0
        self._setup_tracks(display_queue)

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

    def _setup_tracks(self, display_queue):
        self.tracks = []
        for track_id in range(self.nof_tracks):
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
                display_queue=display_queue,
                select=select,
            )
            self.tracks.append(track)

    def _get_midimsgs_from_tracks(self):
        msgs = []
        tracks = [tr for tr in self.tracks if tr.solo]
        if len(tracks) == 0:
            tracks = [tr for tr in self.tracks if not tr.mute]

        for tr in tracks:
            step_val = tr.get_state()[self._current_beat]
            if step_val > 0:
                track_id = tr.track_id
                track_msg = mido.Message(
                    type="note_on",
                    note=self.note_output_map[track_id],
                    velocity=step_val,
                    channel=self.output_channel
                )
                msgs.append(track_msg.bytes())
        return msgs

    def _step_id_from_note_map(self, note):
        step_id = self.note_input_map.index(note)
        step_id = step_id % self.nof_steps
        return step_id

    # Process step events
    def process_step_event(self, note, value):
        if note in self.note_input_map:
            target_track_id = self.display.get_target_track(note)
            step_id = self._step_id_from_note_map(note)
            print("procces", target_track_id, step_id)
            self.tracks[target_track_id](step_id, value)

    # Process track events
    # - track events: select, mute, solo, track state
    # - sequencer events:
    def process_track_event(self, note, value):
        if note in self.track_select_map:
            selected_tracks = self.track_controller.get_selected_tracks(note)
            self.select_tracks(selected_tracks)
        elif note in self.track_controls_map:
            # ToDo := solo/mute for each track
            pass

    def get_track_state(self, track_id):
        return self.tracks[track_id].get_state()

    def get_all_track_states(self, track_id):
        return [tr.get_state() for tr in self.tracks]

    def select_single_track(self, track_id):
        self.select_tracks([track_id])

    def select_tracks(self, track_ids):
        unselect = [
            id for id in range(len(self.tracks)) if id not in track_ids
        ]
        for idx in unselect:
            self.tracks[idx].select = False

        for idx in track_ids:
            self.tracks[idx].select = True

    def selected_tracks(self):
        return [tr for tr in self.tracks if tr.select]

    # Step the sequencer
    def tick(self):
        # pass
        # print("tick")
        msgs = self._get_midimsgs_from_tracks()
        self.output_queue.put(msgs)
        self._current_beat = (self._current_beat + 1) % self.nof_steps

    def start(self):
        self._current_beat = 0

    def stop(self):
        self._current_beat = 0
