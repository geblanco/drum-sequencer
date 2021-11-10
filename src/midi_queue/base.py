import queue
import threading


class MidiQueue(threading.Thread):
    """
        ABC for Midi Queues
    """
    def __init__(self, *args, **kwargs):
        super(MidiQueue, self).__init__()
        # self._wallclock = time.time()
        self.queue = queue.Queue()
        self.args = args
        self.__dict__.update(kwargs)

    def __call__(self, message, data=None):
        """
            This is the main callback, it enqueues messages to be processed
            by the running method
        """
        # self._wallclock += deltatime
        if (
            isinstance(message, (tuple, list)) and
            len(message) == 2 and
            isinstance(message[1], (int, float))
        ):
            # skip the timestamp
            message, _ = message

        if self.filter(message):
            self.queue.put(message)

    def filter(self, message):
        """
            Override this method to filter messages out.
            Let anything through by default
        """
        return True

    def run(self):
        while True:
            message = self.queue.get()

            if message is None:
                break

            self.process(message)

    def process(self, message):
        raise ValueError(
            "You must override `process` method to do something with incoming"
            " messages"
        )

    def stop(self):
        self.queue.put(None)

    def put(self, data):
        self.queue.put(data)
