import mido

from modes import NoteMode, LedMode, LedColors, TrackMode


class Track(object):

    def __init__(
        self,
        track_id,
        config,
        note_input_map,
        led_queue,
        select=False,
        mute=False,
        solo=False,
    ):
        led_config = config["led_config"]
        self.config = config
        self.led_config = led_config

        self.track_id = track_id
        self.note_input_map = note_input_map
        self.led_queue = led_queue

        self._select = select
        self._mute = mute
        self._solo = solo

        self.track_mode = config.get("track_mode", TrackMode.select_tracks)
        self.note_mode = config.get("note_mode", NoteMode.toggle)
        self.nof_steps = config.get("nof_steps", 16)

        self.led_mode = led_config.get("led_mode", LedMode.handled)
        self.led_color_mode = led_config.get(
            "led_color_mode", LedColors.default
        )
        self.led_output_map = led_config["led_output_map"]
        self.led_channel = led_config.get("led_channel", 0)
        self.track_velocity = 127
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
            self.track_velocity = led_config["led_colors"][self.track_id]

        self.state = [0] * self.nof_steps
        # light off leds
        self.propagate()

    def __call__(self, message):
        # ToDo :=
        # - get step, change state
        # - propagate state
        target_step = self.note_input_map.index(message.note)
        if self.note_mode == NoteMode.toggle:
            self.state[target_step] = 127 - self.state[target_step]
        else:
            self.state[target_step] = message.velocity

        self.propagate(target_step)

    @property
    def select(self):
        return self._select

    @select.setter
    def select(self, value):
        self._select = value
        if self._select:
            self.propagate()

    @property
    def mute(self):
        return self._mute

    @mute.setter
    def mute(self, value):
        self._mute = value
        if self._mute:
            self._solo = False

    @property
    def solo(self):
        return self._solo

    @solo.setter
    def solo(self, value):
        self._solo = value
        if self._solo:
            self._mute = False

    def get_state(self):
        return self.state

    def step_ids_to_led_messages(self, step_ids):
        messages = []
        for id in step_ids:
            value = self.state[id]
            if self.led_color_mode == LedColors.velocity and value > 0:
                value = self.track_velocity

            msg = mido.Message(
                type="note_on" if value > 0 else "note_off",
                channel=self.led_channel,
                note=self.led_output_map[id],
                velocity=value,
            )
            messages.append(msg.bytes())

        return messages

    def propagate(self, target_step=None):
        # Light Modes: see class
        if self.track_mode != TrackMode.select_tracks or self.select:
            messages = []
            if self.led_mode == LedMode.handled:
                if target_step is None:
                    step_ids = list(range(len(self.state)))
                else:
                    step_ids = [target_step]

                messages = self.step_ids_to_led_messages(step_ids)
            elif self.led_mode == LedMode.partial_handled:
                # only note-offs
                if target_step is None:
                    step_ids = [st for st in self.state if st == 0]
                else:
                    step_ids = (
                        [self.state[target_step]]
                        if self.state[target_step] == 0
                        else []
                    )
                messages = self.step_ids_to_led_messages(step_ids)

            if len(messages):
                self.led_queue.put(messages)
