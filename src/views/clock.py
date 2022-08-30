from math import sqrt
from .base import ClockedView
from utils import SliceSelector
from modes import SelectMode, ViewMode, LedColors, DisplayMsgTypes


representations = {
    '0': ('###', '# #', '###'),
    '1': ('   ', ' # ', '   '),
    '2': (' # ', ' # ', '   '),
    '3': (' # ', ' # ', ' # '),
    '4': ('   ', '# #', '# #'),
    # '4': (' # ', '# #', ' # '),
    '5': (' # ', '# #', '# #'),
    '6': ('# #', '# #', '# #'),
    '7': ('###', '# #', '# #'),
    '8': ('###', '###', '# #'),
    '9': ('###', '###', '###'),
}


def number_to_segments(number):
    digits = [representations[digit] for digit in str(number)]
    return digits


class ClockSet(ClockedView):
    view_mode = ViewMode.clock_set

    def __init__(self, config, bpm, clock_setter, display_queue):
        self.note_map = config["note_input_map"]
        self.prev_bpm = None
        self.bpm = bpm
        self.set_clock = clock_setter
        self.display_queue = display_queue
        self.setters = config.get("clock_set_map", [])
        self.mult_list = [1, -1, 5, -5, 2, 0.5]
        self.multipliers = []
        self.selectors = []
        self._current_selector = None
        self._skipped_frames = 0
        self._color_pads = config["led_config"].get(
            "led_color_mode", LedColors.default
        ) == LedColors.velocity
        self._paint_controller = (
            # in the future we could scroll the number
            len(self.note_map) >= 64 and self._is_square(self.note_map)
        )
        self._pad_velocity = 127 if self._color_pads else 37
        self._n_rows = self._get_nrows(self.note_map)

        if len(self.setters) < 2:
            raise ValueError(
                "For clock view you must set at least two modifiers!"
            )

        self._setup_selectors()

    def _is_square(self, note_map):
        # Let's assume user made sense on pads...
        return sqrt(len(note_map)) % 2 == 0

    def _get_nrows(self, note_map):
        return int(sqrt(len(note_map)))

    def _setup_selectors(self):
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
        if value > 0:
            self._current_selector = (selector, note)
            selector.toggle(note)
        else:
            self._current_selector = None
            self._skipped_frames = 0

    def _segment_to_notes(self, segment, offset=0, skip_spaces=True):
        notes = []
        for seg_idx, seg in enumerate(segment):
            base_note = seg_idx * self._n_rows
            for idx, ch in enumerate(seg.strip()):
                note_id = offset + base_note + idx
                if not skip_spaces or ch != " ":
                    notes.append(self.note_map[note_id])

        return notes

    def _paint_segment(self, segment, offset=0, velocity=127):
        to_paint = self._segment_to_notes(segment, offset)
        messages = [self.display_msg(note, velocity) for note in to_paint]
        self.display_queue(messages)

    def _segment_density(self, segment):
        mm = max([len(seg.strip()) for seg in segment])
        return mm

    def _segments_offset(self, bpm):
        offsets = [0]
        segments = number_to_segments(bpm)
        densities = [self._segment_density(seg) for seg in segments]
        multi_line = sum(densities) + 2 > self._n_rows
        for idx in range(1, len(segments)):
            if multi_line:
                if idx < 2:
                    offset = idx * 4
                else:
                    offset = 32
            else:
                offset = sum(densities[:idx]) + len(densities[:idx])

            offsets.append(offset)

        return list(zip(offsets, segments))

    def propagate(self):
        print(f"BPM: {self.bpm}")
        if self._paint_controller:
            if self.prev_bpm is not None:
                for offset, segment in self._segments_offset(self.prev_bpm):
                    self.flush_segment(segment, offset=offset)

            for offset, segment in self._segments_offset(self.bpm):
                self._paint_segment(
                    segment, offset=offset, velocity=self._pad_velocity
                )

    def flush_segment(self, segment, offset):
        to_paint = self._segment_to_notes(segment, offset, skip_spaces=False)
        messages = [self.display_msg(note, 0) for note in to_paint]
        self.display_queue(messages)

    def display_msg(self, note, value):
        return [DisplayMsgTypes.one_shot, note, value]

    def filter(self, note, value):
        return any([setter.should_toggle(note) for setter in self.selectors])

    def update_tempo_hook(self, value):
        self.prev_bpm = self.bpm
        self.bpm = value
        self.propagate()
        self.set_clock(self.bpm)

    def tick(self, _):
        if self._current_selector is not None:
            if self._skipped_frames > 2:
                sel = self._current_selector[0]
                val = self._current_selector[1]
                sel.toggle(val)

            self._skipped_frames += 1
