#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# midiclock.py
#
"""Receive MIDI clock and print out current BPM.

MIDI clock (status 0xF8) is sent 24 times per quarter note by clock generators.

"""

import time
import logging
import threading

from rtmidi.midiconstants import (
    TIMING_CLOCK,
    SONG_START,
    SONG_STOP
)


log = logging.getLogger("CLOCK")


class InternalClock(threading.Thread):
    def __init__(self, bpm=120.0, ppqn=24):
        super(InternalClock, self).__init__()
        self._paused = threading.Event()
        self._stopped = threading.Event()
        self._finished = threading.Event()

        self._callback = lambda x: ()

        # run-time options
        self._tick = None
        self.ppqn = ppqn
        self.bpm = bpm

    @property
    def bpm(self):
        return self._bpm

    @bpm.setter
    def bpm(self, value):
        self._bpm = value
        self._tick = 60. / (value * self.ppqn)
        # log.debug("Changed BPM => %s, tick interval %.2f ms.",
        #           self._bpm, self._tick * 1000)

    def set_callback(self, callback):
        self._callback = callback

    def stop(self, timeout=5):
        """Set thread stop event, causing it to exit its mainloop."""
        self._stopped.set()
        # log.debug("SequencerThread stop event set.")

        if self.is_alive():
            self._finished.wait(timeout)

        self.join()

    def pause(self):
        self._paused.set()

    def start(self):
        if not self._paused.is_set():
            self.run()
        else:
            self._paused.clear()

    def run(self):
        self._callback([SONG_START])
        while not self._stopped.is_set():
            while not self._paused.is_set():
                curtime = time.time()

                self._callback([TIMING_CLOCK])

                # loop speed adjustment
                elapsed = time.time() - curtime

                if elapsed < self._tick:
                    time.sleep(self._tick - elapsed)

            time.sleep(1)

        # log.debug("Midi output mainloop exited.")
        self._finished.set()
        self._callback([SONG_STOP])
