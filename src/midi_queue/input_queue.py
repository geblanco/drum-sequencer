import mido

from modes import NoteMode
from .base import MidiQueue
from rtmidi.midiconstants import (
    CONTROLLER_CHANGE,
    NOTE_ON, NOTE_OFF
)
from filters import (
    CCToggle,
    Composite,
    NoteToggle,
    CutThrough,
    ChannelFilter,
)


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
