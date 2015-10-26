"""
Management for multiprocessing in varial.
"""


import multiprocessing.pool
import settings
import signal
import time
import sys
import os


cpu_semaphore = None
_kill_request = None  # initialized to 0, if > 0, the process group is killed
_xcptn_lock = None  # used w/o blocking for _kill_request
pre_fork_cbs = []
pre_join_cbs = []


################################### special worker-pool to allows recursion ###
class _NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False

    def _set_daemon(self, value):
        pass
    daemon = property(_get_daemon, _set_daemon)

    def run(self):
        try:
            super(_NoDaemonProcess, self).run()
        except (KeyboardInterrupt, IOError):
            exit(-1)


class NoDeamonWorkersPool(multiprocessing.pool.Pool):
    Process = _NoDaemonProcess

    def __init__(self, *args, **kws):
        global cpu_semaphore, _kill_request, _xcptn_lock

        # prepare parallelism (only once for the all processes)
        self.me_created_semaphore = False
        if cpu_semaphore:
            # process with pool is supposed to be waiting a lot
            cpu_semaphore.release()
        else:
            self.me_created_semaphore = True
            cpu_semaphore = multiprocessing.BoundedSemaphore(
                                                    settings.max_num_processes)
            _kill_request = multiprocessing.Value('i', 0)
            _xcptn_lock = multiprocessing.RLock()

        for func in pre_fork_cbs:
            func()

        # go parallel
        super(NoDeamonWorkersPool, self).__init__(*args, **kws)

    def __del__(self):
        global cpu_semaphore, _kill_request, _xcptn_lock
        if self.me_created_semaphore:
            cpu_semaphore = None
            _kill_request = None
            _xcptn_lock = None
        else:
            # must re-acquire before leaving
            cpu_semaphore.acquire()

    def imap_unordered(self, func, iterable, chunksize=1):
        def kill_hook(iterable):
            for i in iterable:
                if is_kill_requested():
                    self.close()
                    do_kill_now()
                yield i

        return kill_hook(super(NoDeamonWorkersPool, self).imap_unordered(
            func, iterable, chunksize
        ))

    def close(self):
        for func in pre_join_cbs:
            func()

        super(NoDeamonWorkersPool, self).close()


###################################################### task synchronization ###
def is_kill_requested(request_kill_now=False):
    if request_kill_now:
        if not _xcptn_lock.acquire(block=False):
            return True
        if not _kill_request.value:
            _kill_request.value = 1
            _xcptn_lock.release()
            return False
        _xcptn_lock.release()
        return True
    return bool(_kill_request.value)


def acquire_processing():
    if not cpu_semaphore:
        raise RuntimeError('Should only be called in parallel mode!')
    cpu_semaphore.acquire()


def release_processing():
    if not cpu_semaphore:
        raise RuntimeError('Should only be called in parallel mode!')
    cpu_semaphore.release()


def exec_in_worker(func, *args, **kws):
    """parallel execution with cpu control and exception catching."""

    with cpu_semaphore:
        try:
            return func(*args, **kws)
        except KeyboardInterrupt:  # these will be handled from main process
            pass
        except:  # print exception and request termination
            if not is_kill_requested(request_kill_now=True):
                print '='*80
                print 'EXCEPTION IN PARALLEL EXECUTION START'
                print '='*80
                import traceback
                traceback.print_exception(*sys.exc_info())
                print '='*80
                print 'EXCEPTION IN PARALLEL EXECUTION END'
                print '='*80


def do_kill_now():
    time.sleep(.005)  # 5 millis for not cutting the printout
    os.killpg(os.getpid(), signal.SIGTERM)  # one evil line!
