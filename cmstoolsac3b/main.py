
import signal
import sys
import os
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
            sys.__stdout__.flush()
            self.hits += 1
            settings.recieved_sigint = True
            self.controller.abort_all_processes()


class StdOutTee:
    def __init__(self, logfilename):
        self.logfile = open(logfilename, "w")

    def __del__(self):
        self.logfile.close()

    def write(self, string):
        sys.__stdout__.write(string)
        self.logfile.write(string)

    def flush(self):
        sys.__stdout__.flush()
        self.logfile.flush()


def _process_settings_kws(kws):
    # replace setting, if its name already exists.
    for k,v in kws.iteritems():
        if hasattr(settings, k):
            setattr(settings, k, v)

def _instanciate_samples():
    if not type(settings.samples) is dict:
        settings.samples = sample.load_samples(settings.samples)
    for k,v in settings.samples.items():
        if not isinstance(v, sample.Sample):
            settings.samples[k] = v()

def main(**settings_kws):
    """
    Post processing and processing.

    :type   post_proc_tools: list
    :param  post_proc_tools: ``PostProcTool`` subclasses.
    :type   not_ask_execute:        bool
    :param  not_ask_execute:        Suppress command line input check before
                                    executing the cmsRun processes.
    :type   logfilename:            string
    :param  logfilename:            name of the logfile. No logging if
                                    ``None`` .
    :param  settings_kws:           settings parameters given as keyword
                                    arguments are added to settings, e.g.
                                    ``samples={"mc":MCSample, ...}`` .
    """
    # prepare...
    _process_settings_kws(settings_kws)
    _instanciate_samples()
    app = QtCore.QCoreApplication(sys.argv)
    if settings.logfilename:
        sys.stdout = StdOutTee(settings.logfilename)
        sys.stderr = sys.stdout

    # tweaks in working directory?
    tweak_name = settings.tweak
    if os.path.exists(tweak_name):
        print ("WARNING I found "
               + tweak_name
               + " and I am going to dump it first and then import it!")
        with open(tweak_name, 'r') as f: print f.read()
        import imp
        settings.tweak = imp.load_source(tweak_name[:-3], tweak_name)

    # create folders (for process confs)
    settings.create_folders()

    # controller
    cnt = controller.Controller()
    cnt.setup_processes()
    executed_procs = list(p for p in cnt.waiting_pros if not p.will_reuse_data)

    # post processor
    pst = postprocessing.PostProcessor(not bool(executed_procs))
    cnt.all_finished.connect(pst.run)
    for tool in settings.post_proc_tools:
        #TODO: Move this into PostProcessor!
        assert (isinstance(tool, postprocessing.PostProcTool)
            or issubclass(tool, postprocessing.PostProcTool))
        if not isinstance(tool, postprocessing.PostProcTool):
            tool = tool()
        pst.add_tool(tool)

    # create folders (for plottools)
    settings.create_folders()

    # SIGINT handler
    sig_handler = SigintHandler(cnt)
    signal.signal(signal.SIGINT, sig_handler.handle)

    # connect for quiting
    # (all other finishing connections before this one)
    cnt.all_finished.connect(app.quit)

    # TODO: do not execute postproctools when crtl-c was hit.
    # GO!
    if executed_procs:                          # Got jobs to execute?
        if (settings.not_ask_execute
            or settings.suppress_cmsRun_exec
            or raw_input(
                "Really run these processes:\n   "
                + ",\n   ".join(map(str,executed_procs))
                + "\n?? (type 'yes') "
            ) == "yes"):
            cnt.start_processes()
            return app.exec_()
        else:
            print "INFO: Answer was not yes. Starting post-processing..."
            pst.run()
    elif settings.post_proc_tools:              # No jobs, but post-proc..
        pst.run()
    else:                                       # Nothing to do.
        print "I've got nothing to do!"

def standalone(post_proc_tool_classes, **settings_kws):
    """
    Runs post processing alone.

    :param post_proc_tool_classes:  list of ``PostProcTool`` subclasses.
    :param  settings_kws:           settings parameters given as keyword
                                    arguments are added to settings, e.g.
                                    ``samples={"mc":MCSample, ...}`` .
    """
    _process_settings_kws(settings_kws)
    _instanciate_samples()
    settings.create_folders()

    pst = postprocessing.PostProcessor(False)
    for tool in post_proc_tool_classes:
        pst.add_tool(tool())
    settings.create_folders()
    pst.run()


#TODO: reimplement buildFollowUp

