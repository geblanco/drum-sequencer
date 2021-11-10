from modes import NoteMode, LedMode, LedColors, TrackMode, DisplayMsgTypes


class Track(object):

    def __init__(
        self,
        track_id,
        config,
        display_queue,
        track_controller,
        select=False,
        mute=False,
        solo=False,
    ):
        led_config = config["led_config"]
        self.config = config
        self.led_config = led_config

        self.track_id = track_id

        self._select = select
        self._mute = mute
        self._solo = solo

        self.track_mode = self.config.get(
            "track_mode", TrackMode.select_tracks
        )
        self.note_mode = self.config.get("note_mode", NoteMode.toggle)
        self.nof_steps = self.config.get("nof_steps", 16)

        self.display_queue = display_queue
        self.controller = track_controller
        self.led_mode = self.led_config.get("led_mode", LedMode.handled)
        self.led_color_mode = self.led_config.get(
            "led_color_mode", LedColors.default
        )
        self.track_velocity = self.config.get("note_velocity", 127)
        self.track_velocity = [self.track_velocity] * self.nof_steps
        if (
            "led_colors" not in led_config and
            self.led_color_mode == LedColors.velocity
        ):
            raise RuntimeError(
                "When using velocity pads, you must setup track colors "
                "through `led_config.led_colors` with one velocity value for "
                "each track. Either set it or disable velocity pads all "
                "together with `led_config.led_color_mode: default`"
            )
        elif self.led_color_mode == LedColors.velocity:
            self.track_color = led_config["led_colors"][self.track_id]

        self.state = [0] * self.nof_steps
        # light off leds
        self.propagate()

    def __call__(self, step, value):
        if self.note_mode == NoteMode.toggle:
            self.state[step] = self.track_velocity[step] - self.state[step]
            # self.state[step] = 127 - self.state[step]
        else:
            self.state[step] = value

        self.propagate(step)

    def __repr__(self):
        state = ', '.join(['-' if i == 0 else 'X' for i in self.state])
        state = f"Track {self.track_id}: [{state}]"
        state = f"{state} - [{'SEL' if self.select else 'X'}, "\
            f"{'S' if self._solo else 'X'}, {'M' if self._mute else 'X'}]"

        return state

    def __str__(self):
        return self.__repr__()

    @property
    def select(self):
        return self._select

    @select.setter
    def select(self, value):
        self._select = value
        if self._select:
            self.propagate()
            self.propagate_controls()

    @property
    def mute(self):
        return self._mute

    @mute.setter
    def mute(self, value):
        self._mute = value
        if self._mute:
            self._solo = False
        self.propagate_controls()

    @property
    def solo(self):
        return self._solo

    @solo.setter
    def solo(self, value):
        self._solo = value
        if self._solo:
            self._mute = False
        self.propagate_controls()

    def get_velocity(self):
        return self.track_velocity

    def set_velocity(self, values):
        if isinstance(values, (list, tuple)):
            assert(len(values) == self.nof_steps)
        else:
            values = [values] * self.nof_steps

        for i, val in enumerate(values):
            self.track_velocity[i] = val

    def get_state(self):
        return self.state

    def get_step_velocity(self, step_id):
        value = self.state[step_id]
        if self.led_color_mode == LedColors.velocity and value > 0:
            value = self.track_color

        return value

    def step_ids_to_led_messages(self, step_ids):
        messages = []
        for id in step_ids:
            value = self.get_step_velocity(id)
            note = self.controller.get_track_step_note(self.track_id, id)
            msg = [DisplayMsgTypes.track, self.track_id, note, value]
            messages.append(msg)

        return messages

    def propagate(self, target_step=None):
        # Light Modes: see class
        if self.track_mode != TrackMode.select_tracks or self.select:
            messages = []
            step_ids = []
            if target_step is not None:
                if (
                    self.led_mode == LedMode.handled or
                    (
                        self.led_mode == LedMode.partial_handled and
                        self.state[target_step] == 0
                    )
                ):
                    step_ids.append(target_step)
            else:
                if self.led_mode == LedMode.handled:
                    step_ids = list(range(len(self.state)))
                elif self.led_mode == LedMode.partial_handled:
                    step_ids = [
                        id for id, val in enumerate(self.state) if val == 0
                    ]

            messages = self.step_ids_to_led_messages(step_ids)

            if len(messages):
                # print("Sending led message", messages)
                self.display_queue(messages)

    def propagate_controls(self):
        messages = []
        for control in ["solo", "mute"]:
            note = self.controller.get_control_target_note(
                self.track_id, control
            )
            vel = 127 if getattr(self, control) else 0
            messages.append([DisplayMsgTypes.track, self.track_id, note, vel])

        self.display_queue(messages)
