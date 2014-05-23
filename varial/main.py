import atexit
import signal
import sys
import threading
import time

import analysis
import settings
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


class StdOutTee(object):
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

    def close(self):
        sys.__stdout__.close()
        self.logfile.close()


def _process_settings_kws(kws):
    # replace setting, if its name already exists.
    for k, v in kws.iteritems():
        if hasattr(settings, k):
            setattr(settings, k, v)


class Timer(object):
    keep_alive = True

    def timer_func(self):
        while self.keep_alive:
            time.sleep(1)

    def kill(self):
        self.keep_alive = False

timer       = Timer()
sig_handler = SigintHandler()
exec_thread = threading.Thread(target=timer.timer_func)
exec_start  = exec_thread.start
exec_quit   = timer.kill


def tear_down(*args):
    sig_handler.handle(signal.SIGINT, None)
    time.sleep(1)
    exec_quit()


# iPython mode
def ipython_warn():
    print "WARNING =================================================="
    print "WARNING Detected iPython, going to interactive mode...    "
    print "WARNING =================================================="

if ipython_mode:
    ipython_warn()

    def ipython_exit(*args):
        print "Shutting down..."
        if timer.keep_alive:
            print "Waiting for subprocesses to shutdown..."
            tear_down()
    atexit.register(ipython_exit)

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
    if settings.logfilename:
        import monitor
        monitor.MonitorInfo.outstream = StdOutTee(settings.logfilename)

    # setup samples
    if 'samples' in main_kwargs:
        analysis.all_samples = dict((s.name, s) for s in main_kwargs['samples'])

    # setup toolchain
    global toolchain
    toolchain = main_kwargs.get('toolchain')
    if not toolchain:
        if settings.cmsRun_main_import_path:
            toolchain = tools.CmsRunProxy('cmsrun_output')
        elif settings.fwlite_executable:
            toolchain = tools.FwliteProxy('fwlite_output')
    if not toolchain:
        print "FATAL No toolchain or eventloops scripts defined."
        return
    toolchain = tools.ToolChain(toolchain)  # needed for proper execution


    # GO!
    if ipython_mode:
        exec_thread = threading.Thread(target=toolchain.run)
        return exec_thread.start()
    else:
        toolchain.run()


