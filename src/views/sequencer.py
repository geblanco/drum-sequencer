import mido

from .base import View
from modes import TrackMode, ViewMode
from track import Track
from track import TrackController


class Sequencer(View):
    view_mode = ViewMode.sequencer

    def __init__(
        self,
        config,
        display_queue,
        output_queue,
    ):
        self.config = config
        self.display = display_queue
        self.track_mode = self.config["track_mode"]
        self.output_channel = self.config["output_channel"]
        self.nof_tracks = self.config["nof_tracks"]
        self.nof_steps = self.config["nof_steps"]
        self.note_input_map = self.config["note_input_map"]
        self.note_output_map = self.config["note_output_map"]

        self.track_controller = TrackController(self.config, display_queue)
        self.output_queue = output_queue

        track_select_map = self.config.get("track_select_map", [])
        track_select_mode = self.config["track_select_mode"]

        self._current_beat = 0
        self._setup_tracks(display_queue, track_select_mode)

        if (
            self.track_mode != TrackMode.all_tracks and
            (
                track_select_map is None or
                len(track_select_map) == 0
            ) and
            (self.nof_tracks * self.nof_steps) > len(self.note_input_map)
        ):
            raise ValueError(
                "You must choose track selection values to work with multiple"
                f" tracks in {self.track_mode} mode!"
            )

    def _setup_tracks(self, display_queue, track_select_mode):
        self.tracks = []
        for track_id in range(self.nof_tracks):
            if track_select_mode == TrackMode.all_tracks:
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
                track_controller=self.track_controller,
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

    def __call__(self, note, value):
        if note in self.note_input_map:
            self.process_step_event(note, value)
        else:
            self.process_track_event(note, value)

    def filter(self, note, value):
        return (
            note in self.note_input_map or
            self.track_controller.is_track_control(note)
        )

    # Process step events
    def process_step_event(self, note, value):
        if note in self.note_input_map:
            target_track_id = self.track_controller.get_target_track(note)
            step_id = self.track_controller.get_target_step(note)
            self.tracks[target_track_id](step_id, value)

    # Process track events
    # - track events: mute, solo, track state
    # - select done in omni view (TrackSelect view)
    def process_track_event(self, note, value):
        if self.track_controller.is_track_control(note):
            # ToDo := solo/mute for each track
            target = self.track_controller.get_control_target_track(note)
            self.apply_track_controls(target)
            # for track_id in target.values():
            #     print(self.tracks[track_id])

    def propagate(self):
        for track in self.selected_tracks():
            track.propagate()
            track.propagate_controls()

    def get_track(self, track_id):
        return self.tracks[track_id]

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

    def apply_track_controls(self, target):
        for key, track_id in target.items():
            if key == "solo":
                self.tracks[track_id].solo = not self.tracks[track_id].solo
            else:
                self.tracks[track_id].mute = not self.tracks[track_id].mute

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
