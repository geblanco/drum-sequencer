class View(object):
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
