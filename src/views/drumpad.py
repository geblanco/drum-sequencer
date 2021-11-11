import mido

from .base import View
from modes import DisplayMsgTypes


class Drumpad(View):
    def __init__(self, config, display_queue, output_queue):
        drumpad = config.get("drumpad_input_map", config["note_input_map"])
        self.drumpad = drumpad[:min(len(drumpad), 16)]
        self.multipliers = config.get("drumpad_multiplier_map", [])
        self.drum_velocity = config.get("note_velocity", 127)
        self.note_output_map = config["drumpad_output_map"]
        self.output_channel = config["output_channel"]
        self.display_queue = display_queue
        self.output_queue = output_queue
        self.sync = False
        self._tickcnt = 0
        self._current_signature = None
        self._pad_states = [0] * len(self.drumpad)
        # ToDo := Redo the signatures, wrong inversion
        self._signatures = [
            int(24 / sig) for sig in [1, 2, 3, 4, 8, 16]
        ]

    def _multiplier_on(self):
        return self._current_signature is not None

    def _pad_on(self):
        return any([pad > 0 for pad in self._pad_states])

    def __call__(self, note, value):
        if note in self.drumpad:
            pad_id = self.drumpad.index(note)
            self._pad_states[pad_id] = value
            if value > 0:
                self.output_queue.put(self.drumpad_msg(pad_id))
        elif note in self.multipliers:
            sig = self._signatures[self.multipliers.index(note)]
            if value > 0:
                self._current_signature = sig
            elif self._current_signature == sig:
                self._current_signature = None

            message = self.display_msg(note, 127 if value > 0 else 0)
            self.display_queue(message)

    def filter(self, note, value):
        return note in self.drumpad or note in self.multipliers

    def send_pad_out(self):
        messages = [
            self.drumpad_msg(pad_id)
            for pad_id, pad_val in enumerate(self._pad_states)
            if pad_val > 0
        ]
        self.output_queue.put(messages)

    def drumpad_msg(self, drum_id, to_display=False):
        message = None
        if to_display:
            message = self.display_msg(
                self.drumpad[drum_id], self.drum_velocity
            )
        else:
            message = mido.Message(
                type="note_on",
                note=self.note_output_map[drum_id],
                velocity=self.drum_velocity,
                channel=self.output_channel,
            ).bytes()

        return message

    def display_msg(self, note, value):
        return [DisplayMsgTypes.one_shot, note, value]

    def propagate(self):
        messages = [
            self.drumpad_msg(id, to_display=True)
            for id in range(len(self.drumpad))
        ]
        self.display_queue(messages)

    # ToDo := Review sync mechanism
    def tick(self, tick):
        if self._multiplier_on() and self._pad_on():
            tickcnt = self._tickcnt
            if self.sync:
                tickcnt += tick

            if self._tickcnt % self._current_signature == 0:
                self.send_pad_out()

            self._tickcnt = (tickcnt + 1) % self._current_signature

    def start(self):
        self._tickcnt = 0

    def stop(self):
        self._tickcnt = 0
