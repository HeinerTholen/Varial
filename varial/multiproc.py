"""
Management for multiprocessing in varial.
"""


import multiprocessing.pool

import settings


cpu_semaphore = None
_kill_request = None  # initialized to 0, if > 0, the process group is killed
_xcptn_lock = None  # used w/o blocking for _kill_request
_pre_fork_cbs = []
_pre_join_cbs = []


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

    def __init__(self, processes=None, *args, **kws):
        global cpu_semaphore, _kill_request, _xcptn_lock

        # prepare parallelism (only once for the all processes)
        self.me_created_semaphore = False
        if cpu_semaphore:
            # process with pool is supposed to be waiting a lot
            cpu_semaphore.release()
        else:
            self.me_created_semaphore = True
            cpu_semaphore = multiprocessing.BoundedSemaphore(processes)
            _kill_request = multiprocessing.Value('i', 0)
            _xcptn_lock = multiprocessing.RLock()

        for func in _pre_fork_cbs:
            func()

        # go parallel
        super(NoDeamonWorkersPool, self).__init__(processes, *args, **kws)

    def __del__(self):
        global cpu_semaphore, _kill_request, _xcptn_lock
        if self.me_created_semaphore:
            cpu_semaphore = None
            _kill_request = None
            _xcptn_lock = None
        else:
            # must re-acquire before leaving
            cpu_semaphore.acquire()



    def close(self):
        for func in _pre_join_cbs:
            func()

        super(NoDeamonWorkersPool, self).close()


###################################################### task synchronization ###
def is_kill_requested(request_kill_now=False):
    if request_kill_now:
        if not _xcptn_lock.acquire(block=False):
            _xcptn_lock.release()
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


