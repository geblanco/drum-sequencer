import logging

from .internal_clock import InternalClock
from rtmidi.midiconstants import (
    TIMING_CLOCK, SONG_CONTINUE, SONG_START, SONG_STOP
)

from modes import ClockSource

log = logging.getLogger("Midi Clock")


class Clock(object):
    def __init__(self, clock_source, midiin, bpm=None, signature=4):
        self.clock_source = clock_source
        self.midiin = midiin
        self.bpm = bpm if bpm is not None else 120.0
        self.running = False
        self._tickcnt = 0
        self._signature = int((4 / signature) * 24)

        self._clock_handlers = []
        self._drain_handlers = []
        self._internal_clock = None

        if clock_source != ClockSource.internal:
            midiin.ignore_types(timing=False)
            midiin.set_callback(self)
        else:
            self._create_internal_clock()

    def __call__(self, message, data=None):
        if isinstance(message, (tuple, list)) and len(message) == 2:
            # skip the timestamp
            message, _ = message

        if message[0] == TIMING_CLOCK:
            if self._tickcnt % self._signature == 0:
                for clk_hand in self._clock_handlers:
                    clk_hand.tick()

            self._tickcnt = (self._tickcnt + 1) % self._signature

        elif message[0] in (SONG_CONTINUE, SONG_START):
            self.running = True
            log.info("START/CONTINUE received.")
            for clk_hand in self._clock_handlers:
                clk_hand.start()

        elif message[0] == SONG_STOP:
            self.running = False
            self._tickcnt = 0
            log.info("STOP received.")
            for clk_hand in self._clock_handlers:
                clk_hand.stop()

        else:
            for drain_hand in self._drain_handlers:
                drain_hand(message, data=data)

    def _create_internal_clock(self):
        self._internal_clock = InternalClock(self.bpm)
        self._internal_clock.set_callback(self)

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
        self.running = True
        if self.clock_source == ClockSource.internal:
            if self._internal_clock is None:
                self._create_internal_clock()

            self._internal_clock.start()

    def stop(self):
        self.running = False
        if self.clock_source == ClockSource.internal:
            if self._internal_clock is not None:
                self._internal_clock.stop()

            self._internal_clock = None
