from .base import ClockedView
from utils import SliceSelector
from modes import SelectMode, ViewMode


class ClockSet(ClockedView):
    view_mode = ViewMode.clock_set

    def __init__(self, config, bpm, clock_setter, display_queue):
        self.bpm = bpm
        self.set_clock = clock_setter
        self.display_queue = display_queue
        self.setters = config.get("clock_set_map", [])
        self.mult_list = [1, -1, 5, -5, 2, 0.5]
        self.multipliers = []
        self.selectors = []
        self._current_selector = None
        self._skipped_frames = 0

        if len(self.setters) < 2:
            raise ValueError(
                "For clock view you must set at least two modifiers!"
            )

        total = min([len(self.setters), len(self.mult_list)])
        for idx in range(0, total, 2):
            setters = self.setters[idx:idx + 2]
            multipliers = self.mult_list[idx:idx+2]

            selector = SliceSelector(
                sel_mode=SelectMode.arrows,
                sel_map=setters,
                nof_displayed_opts=1,
                max_opts=300,
                min_index=20,
                start_index=self.bpm,
                increment=multipliers[0],
                update_hook=self.update_tempo_hook
            )
            self.selectors.append(selector)

    def _get_selector(self, note):
        return [sel for sel in self.selectors if sel.should_toggle(note)][0]

    def __call__(self, note, value):
        selector = self._get_selector(note)
        print("Calling the clock", note, value, selector.increment)
        if value > 0:
            self._current_selector = (selector, note)
            selector.toggle(note)
        else:
            self._current_selector = None
            self._skipped_frames = 0

    def propagate(self):
        pass

    def filter(self, note, value):
        return any([setter.should_toggle(note) for setter in self.selectors])

    def update_tempo_hook(self, value):
        print("Updating tempo", value)
        self.bpm = value
        # self.propagate()
        self.set_clock(self.bpm)

    def tick(self, _):
        if self._current_selector is not None:
            if self._skipped_frames > 2:
                sel = self._current_selector[0]
                val = self._current_selector[1]
                sel.toggle(val)

            self._skipped_frames += 1
