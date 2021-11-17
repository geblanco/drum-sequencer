class View(object):
    view_mode = None
    clock_slave = False

    def __call__(self, note, value):
        raise NotImplementedError(
            "You must implement `__call__` method on every View!"
        )

    def propagate(self):
        raise NotImplementedError(
            "You must implement `propagate` method on every View!"
        )

    def filter(self, note, value):
        raise NotImplementedError(
            "You must implement `filter` method on every View!"
        )


class ClockedView(object):
    clock_slave = True

    def tick(self, tick):
        pass

    def start(self):
        pass

    def stop(self):
        pass
