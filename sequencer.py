import math
import mido

from track import Track
from modes import TrackMode, NoteMode


# ToDo :=
# - maps: track_select (in TrackMode.select_tracks) note in, note out
#   track select map maps note to track
#   - should be propagated
#   note_in map are notes mapped to steps
#   - input note, output led
#   note_out map are notes mapped to tracks, each track emmits only on a note
#   - track -> output note
# - think about outputs
class Sequencer(object):
    def __init__(
        self,
        track_mode,
        output_channel=0,
        output_queue=None,
        nof_tracks=8,
        steps_per_track=16,
        track_select_map=None,
        note_input_map=None,
        note_output_map=None,
        note_mode=NoteMode.toggle,
        led_config=None,
        led_queue=None,
    ):
        self.track_mode = track_mode
        self.output_channel = output_channel
        self.output_queue = output_queue
        self.nof_tracks = nof_tracks
        self.steps_per_track = steps_per_track
        self.track_select_map = track_select_map
        self.note_input_map = note_input_map
        self.note_output_map = note_output_map
        self.note_mode = note_mode
        self.led_config = led_config
        self.led_queue = led_queue

        self._current_beat = 0
        self._setup_tracks()

        if (
            self.track_mode != TrackMode.all_tracks and
            track_select_map is None and
            self.nof_tracks > len(self.note_input_map)
        ):
            raise ValueError(
                "You must choose track selection values to work with multiple"
                f" tracks in {self.track_mode} mode!"
            )

    def _setup_tracks(self):
        self.tracks = []
        for track_id in range(self.nof_tracks):
            if self.track_mode == TrackMode.all_tracks:
                start = track_id * self.steps_per_track
                end = (track_id * self.steps_per_track + self.steps_per_track)
            else:
                start = 0
                end = self.steps_per_track
            # ToDo := notes map
            track = Track(
                track_id=track_id,
                track_mode=self.track_mode,
                note_mode=self.note_mode,
                nof_steps=self.steps_per_track,
                note_input_map=self.note_input_map[start:end],
                led_mode=self.led_config.led_mode,
                led_output_map=self.led_config.led_map_out[start:end],
                led_channel=self.led_config.led_channel,
                led_queue=self.led_queue
            )
            self.tracks.append(track)
        self.tracks[0].select = True

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

    def _selected_track(self):
        return [tr for tr in self.tracks if tr.select][0]

    def _track_id_from_note_map(self, note):
        track_id = self.note_input_map.index(note)
        track_id = math.floor(track_id / self.steps_per_track)
        return track_id

    def _select_track(self, track_id):
        unselect = [id for id in range(len(self.tracks)) if id != track_id]
        for idx in unselect:
            self.tracks[idx].select = False

        self.tracks[track_id].select = True

    # Process track events
    def process(self, message):
        if self.track_mode == TrackMode.select_tracks:
            if message.note in self.note_input_map:
                self._selected_track()(message)
            elif message.note in self.track_select_map:
                target_track_id = self.track_select_map.index(message.note)
                self._select_track(target_track_id)
        elif self.track_mode == TrackMode.all_tracks:
            if message.note in self.note_input_map:
                target_track_id = self._track_id_from_note_map(message.note)
                self.tracks[target_track_id](message)

    # Step the sequencer
    def tick(self):
        print("tick")
        msgs = self._get_midimsgs_from_tracks()
        self.output_queue.put(msgs)
        self._current_beat = (self._current_beat + 1) % self.steps_per_track

    def start(self):
        self._current_beat = 0

    def stop(self):
        self._current_beat = 0
