

class Singleton(type):
    """
    Use as metaclass! Example use in ``utilities/monitor.py`` .
    """

    def __init__(self, *args, **kws):
        super(Singleton, self).__init__(*args, **kws)
        self._instance = None


    def __call__(self, *args, **kws):
        if not self._instance:
            self._instance = super(Singleton, self).__call__(*args, **kws)
        return self._instance
