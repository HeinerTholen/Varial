"""
Management for multiprocessing in varial.
"""

import multiprocessing.pool
import settings
import sys

cpu_semaphore = None
_stacktrace_print_lock = None  # this is never released (only print once)
pre_fork_cbs = []
pre_join_cbs = []


############################## errors handling: catch and raise on hostside ###
def _catch_exception_in_worker(func, *args, **kws):
    try:
        res = func(*args, **kws)

    except Exception as e:
        res = 'Exception', e.__class__, e.args
        if _stacktrace_print_lock.acquire(block=False):
            print '='*80
            print 'EXCEPTION IN PARALLEL EXECUTION START'
            print '='*80
            import traceback
            traceback.print_exception(*sys.exc_info())
            print '='*80
            print 'EXCEPTION IN PARALLEL EXECUTION END'
            print '='*80

    except KeyboardInterrupt as e:
        res = 'Exception', e.__class__, e.args

    return res


def _gen_raise_exception_in_host(iterator):
    for i in iterator:
        if isinstance(i, tuple) and len(i) == 3 and i[0] == 'Exception':
            raise i[1](*i[2])
        else:
            yield i


def _exec_in_worker(func_and_item):
    """parallel execution with cpu control and exception catching."""

    with cpu_semaphore:
        return _catch_exception_in_worker(*func_and_item)


################################ special worker-pool to allow for recursion ###
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
        global cpu_semaphore, _stacktrace_print_lock

        # prepare parallelism (only once for the all processes)
        self.me_created_semaphore = False
        if cpu_semaphore:
            # process with pool is supposed to be waiting a lot
            cpu_semaphore.release()
        else:
            self.me_created_semaphore = True
            n_procs = settings.max_num_processes
            cpu_semaphore = multiprocessing.BoundedSemaphore(n_procs)
            _stacktrace_print_lock = multiprocessing.RLock()

        for func in pre_fork_cbs:
            func()

        # go parallel
        super(NoDeamonWorkersPool, self).__init__(*args, **kws)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self.join()

    def imap_unordered(self, func, iterable, chunksize=1):
        iterable = ((func, i) for i in iterable)
        res = super(NoDeamonWorkersPool, self).imap_unordered(
            _exec_in_worker, iterable, chunksize
        )
        res = _gen_raise_exception_in_host(res)
        return res

    def close(self):
        global cpu_semaphore, _stacktrace_print_lock

        for func in pre_join_cbs:
            func()

        if self.me_created_semaphore:
            cpu_semaphore = None
            _stacktrace_print_lock = None
        else:
            # must re-acquire before leaving
            cpu_semaphore.acquire()

        super(NoDeamonWorkersPool, self).close()
