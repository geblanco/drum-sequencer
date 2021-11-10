from .base import MidiQueue


class OutputQueue(MidiQueue):
    def __init__(self, midiout, channel):
        super(OutputQueue, self).__init__(midiout=midiout, channel=channel)

    def process(self, message):
        if len(message):
            # ToDo := Maybe add channel changer
            if isinstance(message, list) and isinstance(message[0], list):
                # bulk
                for msg in message:
                    self.midiout.send_message(msg)
            else:
                self.midiout.send_message(message)
