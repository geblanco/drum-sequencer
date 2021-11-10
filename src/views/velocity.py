from .base import View
from modes import DisplayMsgTypes


def mean(arr):
    return sum(arr) // len(arr)


def argmin(arr):
    min_val = min(arr)
    minn = [
        idx for idx, value in enumerate(arr)
        if value == min_val
    ][0]
    return minn



# ToDo := Allow track select in this view
class Velocity(View):
    def __init__(self, config, track_controller, track_getter, display_queue):
        self.nof_steps = config["nof_steps"]
        self.controller = track_controller
        self.get_track = track_getter
        self.display_queue = display_queue
        self.vels_to_steps = list(range(0, 127, 127 // (self.nof_steps - 1)))

    def __call__(self, note, value):
        pass

    def vel_to_step_id(self, velocity):
        nearest_vels = [abs(vel - velocity) for vel in self.vels_to_steps]
        return argmin(nearest_vels)

    def display_track_velocity(self, track_id):
        messages = []
        track = self.get_track(track_id)
        track_velocity = mean(track.get_velocity())
        velocity_step = self.vel_to_step_id(track_velocity)
        for step_id in range(velocity_step):
            note = self.controller.get_track_step_note(track_id, step_id)
            value = track.get_step_velocity(step_id)
            msg = [DisplayMsgTypes, track_id, note, value]
            messages.append(msg)

        return self.display_queue(messages)

    def propagate(self):
        track_ids = self.controller.get_displayed_track_ids()
        print("selected tracks", track_ids)
        for track_id in self.controller.get_displayed_track_ids():
            self.display_track_velocity(track_id)
