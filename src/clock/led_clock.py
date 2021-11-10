import mido
from modes import DisplayMsgTypes


class LedClock(object):
    def __init__(self, config, track_state_getter, display_queue):
        super(LedClock, self).__init__()
        led_config = config["led_config"]

        self.nof_displayed_tracks = config["nof_displayed_tracks"]
        self.nof_tracks = config["nof_displayed_tracks"]
        self.nof_steps = config["nof_steps"]
        self.led_output_map = led_config.get(
            "led_output_map", config["note_input_map"]
        )
        self.display_queue = display_queue
        self.led_channel = led_config.get("led_channel", 0)
        self.velocities = led_config.get(
            "led_colors", [127] * self.nof_tracks
        )
        self.note_map = config["note_input_map"]
        self.track_state_getter = track_state_getter
        self._current_beat = 0

    def msg_from_tick_track(self, tick, track_id, vel_id, msg_on=True):
        note_id = (track_id * self.nof_steps) + tick
        note = self.note_map[note_id]
        velocity = self.velocities[vel_id] if msg_on else 0

        return mido.Message(
            type="note_on" if msg_on else "note_off",
            channel=self.led_channel,
            note=note,
            velocity=velocity,
        )

    def tick(self):
        messages = []
        for track_id in range(self.nof_displayed_tracks):
            target_track_id = track_id + self.display_queue.display_index
            prev_tick = (self._current_beat - 1) % self.nof_steps
            track_state = self.track_state_getter(target_track_id)
            if track_state[self._current_beat] == 0:
                on_msg = self.msg_from_tick_track(
                    self._current_beat, track_id, target_track_id
                )
                messages.append([DisplayMsgTypes.clock, on_msg.bytes()])

            if track_state[prev_tick] == 0:
                off_msg = self.msg_from_tick_track(
                    prev_tick, track_id, target_track_id, False
                )
                messages.append([DisplayMsgTypes.clock, off_msg.bytes()])

            # else step already lit, no note off or note on

        if len(messages) > 0:
            self.display_queue(messages)

        self._current_beat = (self._current_beat + 1) % self.nof_steps

    def start(self):
        self._current_beat = 0

    def stop(self):
        self._current_beat = 0
