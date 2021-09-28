import mido
import time

from modes import NoteMode


class Guesser:

    def __init__(self, midiin, midiout):
        self.midiin = midiin
        self.midiout = midiout
        self.waiter = MidiWaiter(midiin, midiout, max_retries=-1)

    @staticmethod
    def fill_anchors(anchors, step=4):
        guessed = []
        dir = -1 if anchors[-2] - anchors[-1] > 0 else 1
        anchors.append(anchors[-1] + (dir * step))
        for i in range(1, len(anchors)):
            start = anchors[i-1]
            end = anchors[i]
            if abs(start-end) % step != 0:
                # row skip
                end = start + (dir * step)
            guessed.extend([start + (dir * i) for i in range(step)])
            # else contiguous
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

    def guess_one_track(self, amount, step=4):
        anchors = []
        for pad_id in range(1, amount + 1, step):
            print(f"Select pad number: {pad_id}")
            query_pad = self.waiter.wait_for_key(NoteMode.toggle)
            anchors.append(query_pad.note)

        if len(anchors) == amount:
            return anchors

        return Guesser.fill_anchors(anchors)

    def guess_tracks(self, first_track_map, amount):
        guessed = []
        for i in range(0, amount):
            print(f"Select first pad of track {i + 2}")
            query_pad = self.waiter.wait_for_key(NoteMode.toggle)
            diff = first_track_map[0] - query_pad.note
            guessed.append(query_pad.note)
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
        while message != None:
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


__all__ = ["Guesser", "MidiWaiter"]
