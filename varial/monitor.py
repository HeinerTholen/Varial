"""
Interface for system outputs.
"""

import sys
import time
import settings


class Messenger(object):
    """
    Message stub. Used to connect to Monitor.
    """
    def __init__(self, connected_obj):
        super(Messenger, self).__init__()
        self.connected_obj = connected_obj

    def __call__(self, message_obj):
        message(self.connected_obj, message_obj)

    def started(self):
        started(self.connected_obj, "INFO started")

    def finished(self):
        finished(self.connected_obj, "INFO finished")


class MonitorInfo(object):
    indent = 0
    n_procs = 0
    error_logs_opened = 0
    outstream = sys.stdout
_info = MonitorInfo()


def write_out(*args):
    for arg in args:
        print >> _info.outstream, arg,
    print >> _info.outstream


def proc_enqueued(process):
    write_out(
        "INFO process enqueued:   cmsRun ",
        process.conf_filename
    )


def proc_started(process):
    if settings.suppress_cmsRun_exec or process.reused_old_data:
        return
    write_out(
        "INFO process started  "+time.ctime()+":   cmsRun ",
        process.conf_filename, "PID: ",
        process.subprocess.pid
    )


def proc_finished(process):
    if settings.suppress_cmsRun_exec or process.reused_old_data:
        return
    if hasattr(settings, "recieved_sigint"):
        write_out(
            "INFO process aborted "+time.ctime()+":   cmsRun ",
            process.conf_filename
        )
    else:
        write_out(
            "INFO process finished "+time.ctime()+":   cmsRun ",
            process.conf_filename
        )


def proc_failed(process):
    write_out(
        "WARNING process FAILED "+time.ctime()+"  :   cmsRun ",
        process.conf_filename
    )
    if not _info.error_logs_opened:
        write_out("_______________________________________begin_cmsRun_logfile")
        with open(process.log_filename, "r") as logfile:
            write_out(logfile.read())
        write_out("______________end of log for " + process.conf_filename)
        write_out("_________________________________________end_cmsRun_logfile")
        _info.error_logs_opened += 1


def all_finished():
    write_out("INFO All processes finished, "+time.ctime())


def started(obj, message_obj):
    message(obj, message_obj)
    _info.indent += 1


def message(sender, string):
    if hasattr(sender, "name"):
        sender = sender.name
    elif not type(sender) == str:
        sender = str(type(sender))
    write_out(_info.indent*"  " + str(string) + " (" + sender + ")")


def finished(obj, message_obj):
    _info.indent -= 1
    message(obj, message_obj)


def connect_controller(controller):
    controller.callbacks_on_all_finished.append(all_finished)


def connect_object_with_messenger(obj):
    obj.messenger = Messenger(obj)
    return obj.messenger


