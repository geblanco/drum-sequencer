import mido

from modes import NoteMode, LedMode, TrackMode


class Track(object):

    note_mode = NoteMode.toggle
    led_mode = LedMode.handled

    def __init__(
        self,
        track_id=0,
        track_mode=TrackMode.select_tracks,
        note_mode=NoteMode.toggle,
        led_mode=LedMode.handled,
        nof_steps=16,
        note_input_map=None,
        led_output_map=None,
        led_channel=0,
        led_queue=None,
    ):
        self.track_id = track_id
        self.track_mode = track_mode
        self.note_mode = note_mode
        self.led_mode = led_mode
        self.nof_steps = nof_steps
        self.note_input_map = note_input_map
        self.led_output_map = led_output_map
        self.led_channel = led_channel
        self.led_queue = led_queue
        self.state = [0] * nof_steps
        self.select = False
        self.mute = False
        self.solo = False
        # light off leds
        self.propagate()

    def __call__(self, message):
        # ToDo :=
        # - get step, change state
        # - propagate state
        midomsg = mido.parse(message)
        target_step = self.note_input_map.index(midomsg.note)
        if self.note_mode == NoteMode.toggle:
            self.state[target_step] = 127 - self.state[target_step]
        else:
            self.state[target_step] = midomsg.velocity

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
            self.solo = False

    @property
    def solo(self):
        return self._solo

    @solo.setter
    def solo(self, value):
        self._solo = value
        if self._solo:
            self.mute = False

    def get_state(self):
        return self.state

    def step_ids_to_led_messages(self, step_ids):
        messages = []
        for id in step_ids:
            vel = self.state[id]
            note = self.led_output_map[id]
            msg = mido.Message(
                type="note_on" if vel > 0 else "note_off",
                channel=self.led_channel,
                note=note,
                velocity=vel,
            )
            messages.append(msg.bytes())

        return messages

    def propagate(self, target_step=None):
        # Light Modes: see class
        if self.track_mode != TrackMode.select_tracks or self.select:
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
