from modes import NoteMode


class Guesser:

    def __init__(self, midiin, midiout):
        self.midiin = midiin
        self.midiout = midiout
        self.waiter = MidiWaiter(midiin, midiout, max_retries=5)

    @staticmethod
    def fill_anchors(anchors):
        guessed = []
        for i in range(0, len(anchors), 2):
            start = anchors[i]
            end = anchors[i + 1]
            dir = -1 if start - end > 0 else 1
            diff = abs((start - end) // 3)
            seq = [start + (diff * j * dir) for j in list(range(0, 4))]
            guessed.extend(seq)

        return guessed

    def guess_one_track(self, amount, step=4):
        anchors = []
        for pad_id in range(1, amount + 1 , step):
            text = f"Select pad number: {card}"
            query_pad = self.waiter.wait_for_key(NoteMode.toggle)
            anchors.append(query_pad.note)

        if len(anchors) == amount:
            return anchors

        return Guesser.fill_anchors(anchors)

    def guess_tracks(self, first_track_map, amount):
        guessed = []
        for i in range(1, amount):
            text = f"Select first pad of track {i + 1}"
            query_pad = self.waiter.wait_for_key(NoteMode.toggle)
            guessed.append(query_pad.note)
            for i in range(1, len(first_track_map)):
                diff = first_track_map[i - 1] - first_track_map[i]
                guessed.append(guessed[-1] + diff)

        return guessed


class MidiWaiter:
    def __init__(self, midiin, midiout, max_retries=-1):
        self.midiin = midiin
        self.midiout = midiout

    def wait_for_message(self, note_mode=None):
        retries = 0
        message = None
        while message is None:
            message, _ = self.midiin.get_message()
            if message is not None:
                message = mido.parse(message)
                if note_mode is not None and note_mode == NoteMode.toggle:
                    if message.type == "note_off":
                        message = None
                        continue
                    else:
                        self.midiout.send_message(message.bytes())
            else:
                print("Waiting for MIDI input...")
                time.sleep(1)
                retries += 1
                if self.max_retries > 0 and retries >= self.max_retries:
                    raise RuntimeError(
                        "Tired of waiting for midi input..."
                    )
                
        return mido.parse(message) if isinstance(message, list) else message
