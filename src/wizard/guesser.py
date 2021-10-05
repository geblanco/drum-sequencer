import mido
import time

from modes import NoteMode
from .prompts import query_num


class Guesser:

    def __init__(self, midiin, midiout):
        self.midiin = midiin
        self.midiout = midiout
        self.waiter = MidiWaiter(midiin, midiout, max_retries=-1)

    @staticmethod
    def fill_anchors(anchors, ncols):
        print("filling anchors", "anchors", anchors, ncols)
        guessed = []
        incr = 1
        dir = -1 if anchors[-2] - anchors[-1] > 0 else 1
        if abs(anchors[-1] - anchors[-2]) > ncols:
            # skip rows, hope for the best...
            incr = abs(anchors[-1] - anchors[-2]) // (ncols - 1)

        for i in range(0, len(anchors), 2):
            start = anchors[i]
            end = anchors[i + 1]
            amount = abs(start - end)
            guessed.extend([start + (dir * i) for i in range(0, amount, incr)])
            guessed.append(end)

        print("guessed", guessed)
        return guessed

    def guess_select_track(self, amount):
        anchors = []
        if amount == 2:
            tokens = ["UP arrow", "DOWN arrow"]
        else:
            tokens = [f"track {i + 1}" for i in range(amount)]

        for token in tokens:
            print(f"Select {token}")
            query_pad = self.waiter.wait_for_key(NoteMode.toggle)
            if query_pad.type == "note_on":
                anchors.append(query_pad.note)
            elif query_pad.type == "control_change":
                anchors.append(query_pad.control)
                # if it is not a control_change, what is it?
            else:
                raise ValueError(
                    "You pressed a weird button, don't know what to do with it"
                    f" here it is: {query_pad}"
                )

        return anchors

    def guess_one_track(self, nof_steps):
        anchors = []
        nrows = query_num(
            "Number of rows?",
            type_=int,
            sample=list(range(1, 6)),
            constraints=[1, 12]
        )
        ncols = query_num(
            "Number of columns?",
            type_=int,
            sample=list(range(1, 6)),
            constraints=[1, 12]
        )
        assert(nof_steps == ncols * nrows)
        for row_id in range(nrows):
            for col_id in [1, ncols]:
                pad_id = (row_id * ncols) + col_id
                print(f"Select pad number: {pad_id}")
                query_pad = self.waiter.wait_for_key(NoteMode.toggle)
                anchors.append(query_pad.note)

        if len(anchors) == nof_steps:
            return anchors

        guessed = Guesser.fill_anchors(anchors, ncols)
        assert(len(guessed) == nof_steps)
        return guessed

    def guess_tracks(self, first_track_map, nof_tracks):
        guessed = []
        for i in range(0, nof_tracks):
            print(f"Select first pad of track {i + 2}")
            query_pad = self.waiter.wait_for_key(NoteMode.toggle)
            diff = first_track_map[0] - query_pad.note
            for i in range(0, len(first_track_map)):
                note = first_track_map[i] - diff
                guessed.append(note)

        return guessed


class MidiWaiter:
    def __init__(self, midiin, midiout, max_retries=-1):
        self.midiin = midiin
        self.midiout = midiout
        self.max_retries = max_retries

    def flush_controller_queue(self):
        message = self.midiin.get_message()
        while message is not None:
            message = self.midiin.get_message()

        # do it twice
        time.sleep(0.5)
        message = self.midiin.get_message()
        while message is not None:
            message = self.midiin.get_message()

    def wait_for_key(self, note_mode=None):
        retries = 0
        message = None
        self.flush_controller_queue()
        print("Waiting for MIDI input...")
        while message is None:
            message = self.midiin.get_message()
            if message is not None:
                message, _ = message
                message = mido.parse(message)
                if note_mode is not None and note_mode == NoteMode.toggle:
                    if message.type == "note_off":
                        message = None
                        continue
                    else:
                        self.midiout.send_message(message.bytes())
            else:
                time.sleep(1)
                retries += 1
                if self.max_retries > 0 and retries >= self.max_retries:
                    raise RuntimeError(
                        "Tired of waiting for midi input..."
                    )

        return mido.parse(message) if isinstance(message, list) else message


# __all__ = ["Guesser", "MidiWaiter"]
