import mido
import math
import queue
import logging
import threading

from modes import NoteMode, InputMode, DisplayMsgTypes, TrackMode
from filters import CutThrough, CCToggle, NoteToggle, ChannelFilter, Composite
from rtmidi.midiconstants import (CONTROLLER_CHANGE, NOTE_ON, NOTE_OFF)


log = logging.getLogger("MIDI Queue")


class MidiQueue(threading.Thread):
    """
        ABC for Midi Queues
    """
    def __init__(self, *args, **kwargs):
        super(MidiQueue, self).__init__()
        # self._wallclock = time.time()
        self.queue = queue.Queue()
        self.args = args
        self.__dict__.update(kwargs)

    def __call__(self, message, data=None):
        """
            This is the main callback, it enqueues messages to be processed
            by the running method
        """
        # self._wallclock += deltatime
        # log.debug("IN: @%0.6f %r", self._wallclock, message)
        if (
            isinstance(message, (tuple, list)) and
            len(message) == 2 and
            isinstance(message[1], (int, float))
        ):
            # skip the timestamp
            message, _ = message

        if self.filter(message):
            self.queue.put(message)

    def filter(self, message):
        """
            Override this method to filter messages out.
            Let anything through by default
        """
        return True

    def run(self):
        while True:
            message = self.queue.get()

            if message is None:
                break

            self.process(message)

    def process(self, message):
        raise ValueError(
            "You must override `process` method to do something with incoming"
            " messages"
        )

    def stop(self):
        self.queue.put(None)

    def put(self, data):
        self.queue.put(data)


# ToDo :=
# - Specific filter for the basics?
# - Allow CC toggle (i.e.: for track selection with arrows?)
class InputQueue(MidiQueue):
    def __init__(self, note_mode=None, channel=0):
        note_mode = NoteMode(
            NoteMode.default if note_mode is None else note_mode
        )
        super(InputQueue, self).__init__(note_mode=note_mode, channel=channel)
        self._handlers = []
        # filter pipeline:
        # - channel filter - note filter if note event, cc filter if cc event
        self._setup_filters()

    def _setup_filters(self):
        self.filters = [ChannelFilter(channels=[self.channel])]
        if self.note_mode == NoteMode.default:
            # no processing, just pass cc and note_on, note_off, as is
            event_types = [CONTROLLER_CHANGE, NOTE_ON, NOTE_OFF]
            self.filters.append(CutThrough(event_types=event_types))
        elif self.note_mode == NoteMode.toggle:
            # allow cc as is, only note_on events with velocity > 0
            # many controllers pass NOTE_ON with volicity and same with
            # veolicty == 0 when released, avoid duplication
            self.filters.append(Composite(CCToggle(), NoteToggle()))

    def filter(self, message):
        return any([filt.match(message) for filt in self.filters])

    def add_handler(self, fn):
        log.debug(f"Added handler: {fn}")
        self._handlers.append(fn)

    def process(self, message):
        if message is not None:
            midomsg = None
            for filt in self.filters:
                message = filt.process(message)
                if message is None:
                    break

            if message is not None:
                midomsg = mido.parse(message)

            if midomsg is not None:
                for hand in self._handlers:
                    hand(midomsg)


class DisplayQueue(MidiQueue):
    def __init__(self, config, led_queue):
        super(DisplayQueue, self).__init__()
        self.track_mode = config["track_mode"]
        self.nof_steps = config["nof_steps"]
        self.nof_displayed_tracks = config["nof_displayed_tracks"]
        self.note_input_map = config["note_input_map"]

        led_config = config["led_config"]
        self.led_channel = led_config.get("led_channel", 0)
        self.led_output_map = led_config.get(
            "led_output_map", config["note_input_map"]
        )
        self.led_queue = led_queue

        self.input_mode = InputMode(0)
        self.display_index = 0

    def _process_step_message(self, message):
        assert(len(message) == 4)
        _, track_id, step_id, step_value = message

        multitrack = (
            self.track_mode == TrackMode.all_tracks or
            self.nof_displayed_tracks > 1
        )
        if multitrack:
            start = (track_id - self.display_index) * self.nof_steps
            end = ((track_id - self.display_index) * self.nof_steps + self.nof_steps)
        else:
            start = 0
            end = self.nof_steps
        end_note = self.led_output_map[start:end][step_id]
        msg = mido.Message(
            type="note_on" if step_value > 0 else "note_off",
            channel=self.led_channel,
            note=end_note,
            velocity=step_value,
        )
        return msg.bytes()

    def get_target_track(self, note):
        track_id = self.note_input_map.index(note)
        track_id = math.floor(track_id / self.nof_steps)
        return track_id + self.display_index

    def set_mode(self, mode):
        self.input_mode = mode

    def filter_single(self, message):
        ret = False
        if len(message):
            msg_type = message[0]
            if (
                msg_type == DisplayMsgTypes.clock and
                self.input_mode == InputMode.sequencer
            ):
                # in sequencer mode we display the clock
                ret = True
            elif (
                msg_type == DisplayMsgTypes.track and
                self.input_mode == InputMode.sequencer
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
                    to_queue.append(self._process_step_message(msg))

            if len(to_queue):
                self.led_queue(to_queue)


class OutputQueue(MidiQueue):
    def __init__(self, midiout, channel):
        super(OutputQueue, self).__init__(midiout=midiout, channel=channel)

    def process(self, message):
        if len(message):
            # ToDo := Maybe add channel changer
            if isinstance(message, list) and isinstance(message[0], list):
                # bulk
                for msg in message:
                    self.midiout.send_message(msg)
            else:
                self.midiout.send_message(message)
