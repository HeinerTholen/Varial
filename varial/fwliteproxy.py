import analysis
import settings
import diskio
import toolinterface


class FwliteProxy(toolinterface.Tool):
    def __init__(self,
                 name=None,
                 py_exe=settings.fwlite_executable):
        super(FwliteProxy, self).__init__(name)
        self.py_exe = py_exe

    def reuse(self):
        pass  # check for samples

    def run(self):
        pass

        # remove old proxy ...

        proxy = diskio.read('fwlite_proxy')
        # proxy.event_files