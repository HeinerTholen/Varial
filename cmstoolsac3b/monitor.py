
import sys
import time
import singleton
import settings
from PyQt4 import QtCore

class QSingleton(singleton.Singleton, type(QtCore.QObject)): pass

class Messenger(QtCore.QObject):
    """
    Message stub. Used to connect to Monitor.

    This class eliminates the need for other classes to subclass
    ``PyQt4.QtCore.QObject`` if messaging is wanted.
    """
    started  = QtCore.pyqtSignal()
    message  = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()


class Monitor(QtCore.QObject):
    """
    Interface for system outputs.

    Can be interfaced to a future GUI. Therefore the PyQt Signal and Slot
    Mechanism is used.
    """
    __metaclass__ = QSingleton
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
        self("INFO process enqueued:   cmsRun ", process.conf_filename)

    def proc_started(self, process):
        if settings.suppress_cmsRun_exec or process.reused_old_data:
            return
        self("INFO process started  "+time.ctime()+":   cmsRun ", process.conf_filename, "PID: ", process.pid())

    def proc_finished(self, process):
        if settings.suppress_cmsRun_exec or process.reused_old_data:
            return
        if hasattr(settings, "recieved_sigint"):
            self("INFO process aborted "+time.ctime()+":   cmsRun ", process.conf_filename)
        else:
            self("INFO process finished "+time.ctime()+":   cmsRun ", process.conf_filename)

    def proc_failed(self, process):
        self("WARNING process FAILED "+time.ctime()+"  :   cmsRun ", process.conf_filename)
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
        self(self.indent*"  " + string + " (" + sender + ")")

    def finished(self, obj, message):
        self.indent -= 1
        self.message(obj, message)

    def connect_controller(self, controller):
        controller.process_enqueued.connect(self.proc_enqueued)
        controller.process_started.connect(self.proc_started)
        controller.process_finished.connect(self.proc_finished)
        controller.process_failed.connect(self.proc_failed)
        controller.all_finished.connect(self.all_finished)
        controller.message.connect(self.message)

    def connect_object_with_messenger(self, obj):
        obj.messenger = Messenger()
        obj.messenger.started.connect(
            lambda: self.started(obj, "INFO started"))
        obj.messenger.message.connect(
            lambda message: self.message(obj, message))
        obj.messenger.finished.connect(
            lambda: self.finished(obj, "INFO finished"))
        return obj.messenger.message.emit


