from modes import InputMode


class Router(object):
    def __init__(self, config, display):
        super(Router, self).__init__()
        self.config = config
        self.input_mode_controls = config.get("input_mode_controls", [])
        self.step_controls = config["note_input_map"]
        self.track_controls = config.get("track_select_map", [])
        self.track_controls.extend(config.get("track_controls_map", []))
        self.display = display

        self.input_mode = InputMode(0)
        self.sequencer_handler = lambda *args: None
        self.one_shot_handler = lambda *args: None
        self.velocities_handler = lambda *args: None
        self.track_handler = lambda *args: None

    def set_sequencer_handler(self, handler):
        self.sequencer_handler = handler

    def set_one_shot_handler(self, handler):
        self.one_shot_handler = handler

    def set_velocities_handler(self, handler):
        self.velocities_handler = handler

    def set_track_handler(self, handler):
        self.track_handler = handler

    def process(self, message):
        if message.type in ["note_on", "note_off"]:
            note = message.note
            value = message.velocity
        elif message.type in ["control_change"]:
            note = message.control
            value = message.value

        if note in self.input_mode_controls:
            self.input_mode = InputMode(self.input_mode_controls.index(note))
            self.display.set_mode(self.input_mode)
        elif note in self.step_controls:
            if self.input_mode == InputMode.sequencer:
                self.sequencer_handler(note, value)
            elif self.input_mode == InputMode.one_shot:
                self.one_shot_handler(note, value)
            else:
                self.velocities_handler(note, value)
        elif note in self.track_controls:
            self.track_handler(note, value)
