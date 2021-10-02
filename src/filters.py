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
        return msg is not None and msg[0] & 0xF0 in self.event_types


class CutThrough(MidiFilter):
    def _process(self, messages):
        return messages

    def process(self, messages):
        ret = None
        if messages is not None:
            if isinstance(messages, list) and len(messages) == 3:
                if self.match(messages):
                    ret = self._process(messages)
            elif messages is not None:
                messages = [
                    self._process(msg) for msg in messages
                    if self.match(msg)
                ]
                if len(messages) > 0:
                    ret = messages

        return ret


class Toggle(CutThrough):

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


class CC(CutThrough):

    event_types = (CONTROLLER_CHANGE,)


class NoteToggle(Toggle):

    event_types = (NOTE_ON,)


class CCToggle(Toggle):

    event_types = (CONTROLLER_CHANGE,)


class ChannelFilter(CutThrough):

    event_types = (NOTE_ON, NOTE_OFF, CONTROLLER_CHANGE)

    def __init__(self, channels):
        super().__init__(channels=channels)

    def match(self, msg):
        return super().match(msg) and msg[0] & 0x0F in self.channels


class Composite(object):

    def __init__(self, *args):
        self.filters = [ar for ar in args]

    def match(self, message):
        return any([filt.match(message) for filt in self.filters])

    def process(self, message):
        ret = None
        target = [filt for filt in self.filters if filt.match(message)]
        if len(target):
            target = target[0]
            ret = target.process(message)

        return ret
