
import os
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

    def __init__(self):
        super(Monitor, self).__init__()
        self.error_logs_opened = 0

    def proc_enqueued(self, process):
        print "INFO process enqueued:   cmsRun ", process.conf_filename

    def proc_started(self, process):
        if settings.suppress_cmsRun_exec or process.reused_old_data:
            return
        print "INFO process started :   cmsRun ", process.conf_filename

    def proc_finished(self, process):
        if settings.suppress_cmsRun_exec or process.reused_old_data:
            return
        print "INFO process finished:   cmsRun ", process.conf_filename

    def proc_failed(self, process):
        print "WARNING process FAILED  :   cmsRun ", process.conf_filename
        if not self.error_logs_opened:
            print "_______________________________________begin_cmsRun_logfile"
            os.system("cat " + process.log_filename)
            print "_________________________________________end_cmsRun_logfile"
            self.error_logs_opened += 1

    def all_finished(self):
        print "INFO All processes finished"

    def message(self, sender, string):
        if not type(sender) == str:
            sender = str(type(sender))
        print string + " (" + sender + ")"

    def connect_controller(self, controller):
        controller.process_enqueued.connect(self.proc_enqueued)
        controller.process_started.connect(self.proc_started)
        controller.process_finished.connect(self.proc_finished)
        controller.process_failed.connect(self.proc_failed)
        controller.all_finished.connect(self.all_finished)
        controller.message.connect(self.message)

    def connect_object_with_messenger(self, obj):
        obj.message = obj.messenger.message.emit
        obj.messenger.started.connect(
            lambda: self.message(obj, "INFO started"))
        obj.messenger.message.connect(
            lambda message: self.message(obj, message))
        obj.messenger.finished.connect(
            lambda: self.message(obj, "INFO finished"))


