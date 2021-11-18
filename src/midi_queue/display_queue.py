import mido

from .base import MidiQueue
from modes import ViewMode, DisplayMsgTypes


class DisplayQueue(MidiQueue):
    def __init__(self, config, led_queue):
        super(DisplayQueue, self).__init__()
        self.track_mode = config["track_mode"]
        self.nof_steps = config["nof_steps"]
        self.nof_displayed_tracks = config["nof_displayed_tracks"]
        self.note_input_map = config["note_input_map"]

        self.track_controls_map = config.get("all_track_controls", [])

        led_config = config["led_config"]
        self.led_channel = led_config.get("led_channel", 0)
        self.led_queue = led_queue

        self.view = ViewMode(ViewMode.sequencer)
        self.display_index = 0

    def _process_note_message(self, note, value):
        msg = mido.Message(
            type="note_on" if value > 0 else "note_off",
            channel=self.led_channel,
            note=note,
            velocity=value,
        )
        return msg.bytes()

    def _is_clock_msg(self, msg_type):
        return msg_type == DisplayMsgTypes.clock

    def _is_track_msg(self, msg_type):
        return msg_type == DisplayMsgTypes.track

    def _is_one_shot_msg(self, msg_type):
        return msg_type == DisplayMsgTypes.one_shot

    def _track_in_display(self, track_id):
        return (
            self.display_index <= track_id and
            track_id < self.display_index + self.nof_displayed_tracks
        )

    def _is_seq_view(self):
        return self.view == ViewMode.sequencer

    def _is_drumpad_view(self):
        return self.view == ViewMode.drumpad

    def _is_velocity_view(self):
        return self.view == ViewMode.velocity

    def _is_clock_set_view(self):
        return self.view == ViewMode.clock_set

    def set_view(self, mode):
        self.view = mode

    def unwrap_message(self, message):
        ret = None
        if len(message):
            msg_type = message[0]
            if self._is_clock_msg(msg_type):
                if self._is_seq_view() or self._is_drumpad_view():
                    # in sequencer and drum mode we display the clock
                    ret = message[1]
            else:
                track_id = message[1]
                valid = False
                if self._track_in_display(track_id):
                    if self._is_seq_view() or self._is_velocity_view():
                        # if track message falls in displayed tracks
                        valid = True
                elif self._is_drumpad_view() or self._is_clock_set_view():
                    # or we are in another view
                    valid = True

                if valid:
                    ret = self._process_note_message(message[-2], message[-1])

        return ret

    def filter_messages(self, messages):
        to_process = []
        multimsg = all([isinstance(ms, (tuple, list)) for ms in messages])
        if not multimsg:
            messages = [messages]

        for msg in messages:
            maybe_msg = self.unwrap_message(msg)
            if maybe_msg is not None:
                to_process.append(maybe_msg)

        return to_process

    def process(self, messages):
        if len(messages):
            to_queue = self.filter_messages(messages)
            if len(to_queue):
                self.led_queue(to_queue)
