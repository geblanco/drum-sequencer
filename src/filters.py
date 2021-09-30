# -*- coding: utf-8 -*-
#
# midifilter/filters.py
#
"""Collection of MIDI filter classes."""

from rtmidi.midiconstants import (CONTROLLER_CHANGE, NOTE_ON, NOTE_OFF)


class MidiFilter(object):
    """ABC for midi filters."""

    event_types = ()

    def __init__(self, *args, **kwargs):
        self.args = args
        self.__dict__.update(kwargs)

    def process(self, messages):
        """Process incoming messages.

        Receives a list of MIDI event tuples (message, timestamp).

        Must return an iterable of event tuples.

        """
        raise NotImplementedError("Abstract method 'process()'.")

    def match(self, msg):
        return msg[0] & 0xF0 in self.event_types


class PassThrough(MidiFilter):

    def process(self, messages):
        return messages


class NoteToggle(MidiFilter):
    event_types = (NOTE_ON,)

    def match(self, msg):
        if super().match(msg):
            return msg[-1] > 0

    def _process(self, message):
        if self.match(message):
            vel = message[-1]
            # should not happe, raise here?
            if vel == 0:
                return None
            else:
                # max velocity
                vel = 127
                message[-1] = vel
                return message

        return message

    def process(self, messages):
        if not isinstance(messages, list):
            return self._process(messages)

        for evt in messages:
            return self._process(evt)


class CC(PassThrough):

    event_types = (CONTROLLER_CHANGE,)


class ChannelFilter(PassThrough):

    event_types = (NOTE_ON, NOTE_OFF, CONTROLLER_CHANGE)

    def __init__(self, channels):
        super().__init__(channels=channels)

    def match(self, msg):
        return super().match(msg) and msg[0] & 0x0F in self.channels
