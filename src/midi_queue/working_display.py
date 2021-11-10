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

        self.input_mode = ViewMode.from_index(0)
        self.display_index = 0

    def _process_note_message(self, message):
        assert(len(message) == 4)
        _, _, note, step_value = message

        msg = mido.Message(
            type="note_on" if step_value > 0 else "note_off",
            channel=self.led_channel,
            note=note,
            velocity=step_value,
        )
        print("Sending", msg.bytes())
        return msg.bytes()

    def set_mode(self, mode):
        self.input_mode = mode

    def filter_single(self, message):
        ret = False
        if len(message):
            msg_type = message[0]
            if (
                msg_type == DisplayMsgTypes.clock and
                self.input_mode == ViewMode.sequencer
            ):
                # in sequencer mode we display the clock
                ret = True
            elif (
                msg_type == DisplayMsgTypes.track and
                self.input_mode == ViewMode.sequencer
            ):
                # if track message falls in displayed tracks
                track_id = message[1]
                if (
                    self.display_index <= track_id and
                    track_id < self.display_index + self.nof_displayed_tracks
                ):
                    ret = True
        return ret

    def process(self, messages):
        if len(messages):
            to_process = []
            multimsg = all([isinstance(ms, (tuple, list)) for ms in messages])
            if multimsg:
                for msg in messages:
                    if self.filter_single(msg):
                        to_process.append(msg)
            else:
                if self.filter_single(messages):
                    to_process.append(messages)

            to_queue = []
            for msg in to_process:
                msg_type = msg[0]
                if msg_type == DisplayMsgTypes.clock:
                    to_queue.append(msg[1])
                elif msg_type == DisplayMsgTypes.track:
                    to_queue.append(self._process_note_message(msg))

            if len(to_queue):
                self.led_queue(to_queue)
