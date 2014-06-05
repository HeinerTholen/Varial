import atexit
import signal
import sys
import threading
import os
import time

import analysis
import settings
import monitor
import tools

ipython_mode = False
try:
    __IPYTHON__
    ipython_mode = True
except NameError:
    pass


class SigintHandler(object):
    def __init__(self):
        self.hits = 0

    def handle(self, signal_int, frame):
        if signal_int is signal.SIGINT:
            if not ipython_mode:
                print "WARNING: aborting all processes. " \
                      "Crtl-C again to kill immediately!"
                if self.hits:
                    exit(-1)
            sys.__stdout__.flush()
            self.hits += 1
            settings.recieved_sigint = True
sig_handler = SigintHandler()


class StdOutTee(object):
    def __init__(self, logfilename):
        self.logfile = open(logfilename, "w")

    def __del__(self):
        self.logfile.close()

    def __getattr__(self, item):
        return getattr(sys.__stdout__, item)

    def write(self, string):
        sys.__stdout__.write(string)
        self.logfile.write(string)

    def flush(self):
        sys.__stdout__.flush()
        self.logfile.flush()

    def close(self):
        sys.__stdout__.close()
        self.logfile.close()


def _process_settings_kws(kws):
    # replace setting, if its name already exists.
    for k, v in kws.iteritems():
        if hasattr(settings, k):
            setattr(settings, k, v)


def tear_down(*args):
    print "Tear down."
    sig_handler.handle(signal.SIGINT, None)
    time.sleep(1)


# iPython mode
def ipython_warn():
    print "WARNING =================================================="
    print "WARNING Detected iPython, going to interactive mode...    "
    print "WARNING =================================================="

if ipython_mode:
    ipython_warn()
    atexit.register(tear_down)

else:
    signal.signal(signal.SIGINT, sig_handler.handle)


###################################################################### main ###
main_args = {}
toolchain = None

def main(**main_kwargs):
    """
    Processing and post processing.

    :param main_kwargs:             settings parameters given as keyword
                                    arguments are added to settings, e.g.
                                    ``samples={"mc":MCSample, ...}`` .
    :param samples:                 list of sample.Sample instances
    :param toolchain:               root toolchain (see tools.py)
    """
    # prepare...
    main_args.update(main_kwargs)
    _process_settings_kws(main_kwargs)
    logfile = settings.logfilename()
    logpath = os.path.split(logfile)[0]
    if not os.path.exists(logpath):
        os.mkdir(logpath)
    monitor.MonitorInfo.outstream = StdOutTee(logfile)

    # setup samples
    if 'samples' in main_kwargs:
        analysis.all_samples = dict((s.name, s) for s in main_kwargs['samples'])

    if 'active_samples' in main_kwargs:
        analysis.active_samples = main_kwargs['active_samples']
    elif not analysis.active_samples:
        analysis.active_samples = analysis.all_samples.keys()

    # setup toolchain
    global toolchain
    toolchain = main_kwargs.get('toolchain')
    if not toolchain:
        if settings.cmsRun_main_import_path:
            toolchain = tools.CmsRunProxy('cmsrun_output')
        elif settings.fwlite_executable:
            toolchain = tools.FwliteProxy('fwlite_output')
    if not toolchain:
        monitor.message(
            'varial.main',
            "FATAL No toolchain or eventloops scripts defined."
        )
        return
    toolchain = tools.ToolChain(None, [toolchain])  # needed for exec
    toolchain._reuse = settings.try_reuse_results

    # GO!
    try:
        toolchain.run()
    except RuntimeError as e:
        if e.args[0] == 'End of reload results mode at: ':
            monitor.message(
                'varial.main',
                'WARNING ' + str(e.args)
            )
        else:
            raise e


