import mido
import queue
import logging
import threading

from modes import NoteMode
from filters import MidiFilter, CC, NoteToggle, ChannelFilter
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
        if isinstance(message, (tuple, list)) and len(message) == 2:
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


# ToDo := Specific filter for the basics?
class InputQueue(MidiQueue):
    def __init__(self, note_mode=None, channel=0):
        note_mode = NoteMode(
            NoteMode.default if note_mode is None else note_mode
        )
        super(InputQueue, self).__init__(note_mode=note_mode, channel=channel)
        self._handlers = []
        self._setup_filters()

    def _setup_filters(self):
        self.filters = [ChannelFilter(channels=[self.channel])]
        if self.note_mode == NoteMode.default:
            # no processing, just pass cc and note_on, note_off, as is
            event_types = [CONTROLLER_CHANGE, NOTE_ON, NOTE_OFF]
            self.filters.append(MidiFilter(event_types=event_types))
        elif self.note_mode == NoteMode.toggle:
            # allow cc as is, only note_on events with velocity > 0
            # many controllers pass NOTE_ON with veolicity and same with
            # veolicty == 0 when released, avoid duplication
            self.filters.extend([CC(), NoteToggle()])

    def filter(self, message):
        return any([filt.match(message) for filt in self.filters])

    def add_handler(self, fn):
        log.debug(f"Added handler: {fn}")
        self._handlers.append(fn)

    def process(self, message):
        if self.note_mode == NoteMode.toggle:
            # only process messages in toggle mode
            for filt in self.filters:
                # only the matching filters will process, the rest will just
                # passthrough
                message = filt.process(message)

        midomsg = mido.parse(message)
        for hand in self._handlers:
            hand(midomsg)


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
