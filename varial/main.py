"""
Main. This module should be used for complete analysis setups.
"""

import ast
import atexit
import signal
import sys
import os
import time

import analysis
import settings
import monitor
import tools
import toolinterface

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
                if self.hits:
                    if toolinterface._n_parallel_workers:
                        try:
                            os.killpg(os.getpid(), signal.SIGTERM)
                        except OSError:
                            time.sleep(1)
                    exit(-1)
                else:
                    print "WARNING: SIGINT caught. " \
                          "Aborting processes if any. " \
                          "Crtl-C again to kill immediately!"
            sys.__stdout__.flush()
            self.hits += 1
            settings.recieved_sigint = True
sig_handler = SigintHandler()


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
    Configure varial and run a toolchain.

    :param main_kwargs:             settings parameters given as keyword
                                    arguments are added to settings, e.g.
                                    ``samples={"mc":MCSample, ...}`` .
    :param samples:                 list of sample.Sample instances
    :param toolchain:               root toolchain (see tools.py)
    """
    if '--settings' in sys.argv:
        import inspect
        print "Memberes of the settings module:"
        for member in dir(settings):
            if member[0] == '_' or inspect.ismodule(member):
                continue
            print "  ", member, "=", getattr(settings, member)
        exit()

    # prepare...
    for arg in sys.argv:
        if 1 == arg.count('='):
            k, v = arg.split('=')
            main_kwargs[k] = ast.literal_eval(v)
    main_args.update(main_kwargs)
    _process_settings_kws(main_kwargs)
    logfile = settings.logfilename()
    logpath = os.path.split(logfile)[0]
    if not os.path.exists(logpath):
        os.mkdir(logpath)
    monitor.MonitorInfo.outstream = monitor.StdOutTee(logfile)

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


#TODO grep "print " *.py and replace them with monitor