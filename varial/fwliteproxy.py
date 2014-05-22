import analysis
import diskio
import toolinterface


class FwliteProxy(toolinterface.Tool):
    def __init__(self, name=None):
        super(FwliteProxy, self).__init__(name)

    def run(self):
        pass

    #with open('proxy.json') as f_proxy:
    #proxy['event_files']