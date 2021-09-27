import time
import logging

from.internal_clock import InternalClock
from collections import deque
from rtmidi.midiconstants import (
    TIMING_CLOCK, SONG_CONTINUE, SONG_START, SONG_STOP
)

from modes import ClockSource

log = logging.getLogger("Midi Clock")


class Clock(object):
    def __init__(self, clock_source, midiin, bpm=None):
        self.clock_source = clock_source
        self.midiin = midiin
        self.bpm = bpm if bpm is not None else 120.0
        self.sync = False
        self.running = True
        self._samples = deque()
        self._last_clock = None

        self._clock_handlers = []
        self._drain_handlers = []
        self._internal_clock = None

        if clock_source != ClockSource.internal:
            midiin.ignore_types(timing=False)
            midiin.set_callback(self)
        else:
            self._internal_clock = InternalClock(self.bpm)
            self._internal_clock.set_callback(self)

    def __call__(self, message, data=None):
        if message[0] == TIMING_CLOCK:
            now = time.time()

            if self._last_clock is not None:
                self._samples.append(now - self._last_clock)

            self._last_clock = now

            if len(self._samples) > 24:
                self._samples.popleft()

            if len(self._samples) >= 2:
                self.bpm = 2.5 / (sum(self._samples) / len(self._samples))
                self.sync = True
                for clk_hand in self._clock_handlers:
                    clk_hand.tick()

        elif message[0] in (SONG_CONTINUE, SONG_START):
            self.running = True
            log.info("START/CONTINUE received.")
            for clk_hand in self._clock_handlers:
                clk_hand.start()

        elif message[0] == SONG_STOP:
            self.running = False
            log.info("STOP received.")
            for clk_hand in self._clock_handlers:
                clk_hand.stop()

        else:
            for drain_hand in self._drain_handlers:
                drain_hand(message, data=data)

    def add_clock_handler(self, obj):
        attr_fns = ["start", "stop", "tick"]
        for attr in attr_fns:
            if getattr(obj, attr, None) is None:
                raise RuntimeError(
                    "Invalid Clock handler, the handler should implement"
                    f" {attr_fns}!. {attr} not found"
                )

        self._clock_handlers.append(obj)

    def add_drain_handler(self, obj):
        self._drain_handlers.append(obj)

    def start(self):
        if self.clock_source == ClockSource.internal:
            self._internal_clock.start()

    def stop(self):
        if self.clock_source == ClockSource.internal:
            self._internal_clock.stop()
