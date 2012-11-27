
import signal
import sys
import settings
import sample
import controller
import postprocessing
from PyQt4 import QtCore

class SigintHandler(object):
    def __init__(self, controller):
        self.controller = controller
        self.hits = 0

    def handle(self, signal_int, frame):
        if signal_int is signal.SIGINT:
            if self.hits:
                exit(-1)
            print "WARNING: aborting all processes. Crtl-C again to kill immediately!"
            self.hits += 1
            self.controller.abort_all_processes()


class StdOutTee:
    def __init__(self, logfilename):
        self.logfile = open(logfilename, "w")

    def __del__(self):
        self.logfile.close()

    def write(self, string):
        sys.__stdout__.write(string)
        self.logfile.write(string)


def main(samples=None,
         cfg_import_path=None,
         post_proc_tool_classes=list(),
         not_ask_execute=False,
         logfilename="cmstoolsac3b.log"):
    """
    Post processing and processing.

    :type   samples:                list
    :param  samples:                ``Sample`` subclasses.
    :type   post_proc_tool_classes: liat
    :param  post_proc_tool_classes: ``PostProcTool`` subclasses.
    :type   not_ask_execute:        bool
    :param  not_ask_execute:        Suppress command line input check before
                                    executing the cmsRun processes.
    :type   logfilename:            string
    :param  logfilename:            name of the logfile. No logging if
                                    ``None``.
    """
    # prepare...
    sample.load_samples(samples)
    if cfg_import_path:
        settings.cfg_main_import_path = cfg_import_path
    settings.create_folders()
    app = QtCore.QCoreApplication(sys.argv)
    if logfilename:
        sys.stdout = StdOutTee(logfilename)
        sys.stderr = sys.stdout

    # controller
    cnt = controller.Controller()
    cnt.setup_processes()
    executed_procs = list(p for p in cnt.waiting_pros if not p.will_reuse_data)

    # post processor
    pst = postprocessing.PostProcessor(not bool(executed_procs))
    cnt.all_finished.connect(pst.run)
    for tool in post_proc_tool_classes:
        assert issubclass(tool, postprocessing.PostProcTool)
        pst.add_tool(tool())

    # SIGINT handler
    sig_handler = SigintHandler(cnt)
    signal.signal(signal.SIGINT, sig_handler.handle)

    # connect for quiting
    # (all other finishing connections before this one)
    cnt.all_finished.connect(app.quit)

    # GO!
    if not cnt.waiting_pros:
        print "INFO: I have no cmsRun jobs. Quitting..."
        exit(-1)
    elif executed_procs:
        if not_ask_execute or input(
            "Really run these processes:\n"
            + str(executed_procs)
            + "\n??? (type 'yes')"
        ) == "yes":
            cnt.start_processes()
    return app.exec_()

def standalone(post_proc_tool_classes, samples=None):
    """
    Runs post processing alone.

    :param post_proc_tool_classes:  list of ``PostProcTool`` subclasses.
    :param samples:                 list of ``Sample`` subclasses. (tools might
                                    depend on sample info, e.g. legend string.)
    """
    sample.load_samples(samples)
    settings.create_folders()

    pst = postprocessing.PostProcessor(False)
    for tool in post_proc_tool_classes:
        pst.add_tool(tool())
    settings.create_folders()
    pst.run()


#TODO: reimplement buildFollowUp

