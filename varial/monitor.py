
import sys
import time
import settings


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


class Messenger(object):
    """
    Message stub. Used to connect to Monitor.
    """
    def __init__(self, connected_obj):
        super(Messenger, self).__init__()
        self.monitor = Monitor()
        self.connected_obj = connected_obj

    def __call__(self, message):
        self.monitor.message(self.connected_obj, message)

    def started(self):
        self.monitor.started(self.connected_obj, "INFO started")

    def finished(self):
        self.monitor.finished(self.connected_obj, "INFO finished")


class Monitor(object):
    """
    Interface for system outputs.

    Can be interfaced to a future GUI. Therefore the PyQt Signal and Slot
    Mechanism is used.
    """
    __metaclass__ = Singleton
    indent = 0
    n_procs = 0

    def __init__(self):
        super(Monitor, self).__init__()
        self.error_logs_opened = 0
        self.outstream = sys.stdout

    def __call__(self, *args):
        for arg in args:
            print >> self.outstream, arg,
        print >> self.outstream

    def proc_enqueued(self, process):
        self(
            "INFO process enqueued:   cmsRun ",
            process.conf_filename
        )

    def proc_started(self, process):
        if settings.suppress_cmsRun_exec or process.reused_old_data:
            return
        self(
            "INFO process started  "+time.ctime()+":   cmsRun ",
            process.conf_filename, "PID: ",
            process.subprocess.pid
        )

    def proc_finished(self, process):
        if settings.suppress_cmsRun_exec or process.reused_old_data:
            return
        if hasattr(settings, "recieved_sigint"):
            self(
                "INFO process aborted "+time.ctime()+":   cmsRun ",
                process.conf_filename
            )
        else:
            self(
                "INFO process finished "+time.ctime()+":   cmsRun ",
                process.conf_filename
            )

    def proc_failed(self, process):
        self(
            "WARNING process FAILED "+time.ctime()+"  :   cmsRun ",
            process.conf_filename
        )
        if not self.error_logs_opened:
            self("_______________________________________begin_cmsRun_logfile")
            with open(process.log_filename, "r") as logfile:
                self(logfile.read())
            self("______________end of log for " + process.conf_filename)
            self("_________________________________________end_cmsRun_logfile")
            self.error_logs_opened += 1

    def all_finished(self):
        self("INFO All processes finished, "+time.ctime())

    def started(self, obj, message):
        self.message(obj, message)
        self.indent += 1

    def message(self, sender, string):
        if hasattr(sender, "name"):
            sender = sender.name
        elif not type(sender) == str:
            sender = str(type(sender))
        self(self.indent*"  " + str(string) + " (" + sender + ")")

    def finished(self, obj, message):
        self.indent -= 1
        self.message(obj, message)

    def connect_controller(self, controller):
        controller.callbacks_on_all_finished.append(self.all_finished)

    def connect_object_with_messenger(self, obj):
        obj.messenger = Messenger(obj)
        return obj.messenger


