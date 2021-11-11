from .base import View
from modes import DisplayMsgTypes, LedColors


def mean(arr):
    return sum(arr) // len(arr)


def argmin(arr):
    min_val = min(arr)
    minn = [
        idx for idx, value in enumerate(arr)
        if value == min_val
    ][0]
    return minn


class Velocity(View):
    def __init__(self, config, track_controller, track_getter, display_queue):
        self.note_input_map = config["note_input_map"]
        self.nof_steps = config["nof_steps"]
        self.controller = track_controller
        self.get_track = track_getter
        self.display_queue = display_queue
        self.vels_to_steps = list(range(1, 127, 127 // (self.nof_steps - 1)))
        self.vels_to_steps[-1] = 127

    def __call__(self, note, value):
        track_id = self.controller.get_target_track(note)
        step_id = self.controller.get_target_step(note)
        velocity = self.step_id_to_vel(step_id)
        self.get_track(track_id).set_velocity(velocity)
        self.flush_track(track_id)
        self.display_track_velocity(track_id)

    def filter(self, note, value):
        return note in self.note_input_map

    def vel_to_step_id(self, velocity):
        nearest_vels = [abs(vel - velocity) for vel in self.vels_to_steps]
        return argmin(nearest_vels)

    def step_id_to_vel(self, step_id):
        return self.vels_to_steps[step_id]

    def flush_track(self, track_id):
        messages = []
        for step_id in range(self.nof_steps):
            note = self.controller.get_track_step_note(track_id, step_id)
            value = 0
            msg = [DisplayMsgTypes, track_id, note, value]
            messages.append(msg)

        return self.display_queue(messages)

    def display_track_velocity(self, track_id):
        messages = []
        track = self.get_track(track_id)
        track_velocity = mean(track.get_velocity())
        velocity_step = self.vel_to_step_id(track_velocity)
        for step_id in range(velocity_step + 1):
            note = self.controller.get_track_step_note(track_id, step_id)
            value = 127
            if track.led_color_mode == LedColors.velocity:
                value = track.track_color
            msg = [DisplayMsgTypes, track_id, note, value]
            messages.append(msg)

        return self.display_queue(messages)

    def propagate(self):
        track_ids = self.controller.get_displayed_track_ids()
        for track_id in self.controller.get_displayed_track_ids():
            self.display_track_velocity(track_id)
