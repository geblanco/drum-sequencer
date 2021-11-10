from .base import View
from modes import DisplayMsgTypes


class Drumpad(View):
    def __init__(self, config, display_queue, output_queue):
        drumpad = config.get("note_drumpad_map", config["note_input_map"])
        self.drumpad = drumpad[:min(len(drumpad), 16)]
        self.drum_velocity = config.get("note_velocity", 127)
        self.display_queue = display_queue
        self.output_queue = output_queue

    def __call__(self, note, value):
        pass

    def drumpad_msg(self, drum_id):
        return [
            DisplayMsgTypes.one_shot,
            self.drumpad[drum_id],
            self.drum_velocity
        ]

    def propagate(self):
        messages = [self.drumpad_msg(id) for id in range(len(self.drumpad))]
        self.display_queue(messages)
