import ROOT
import itertools
import multiprocessing
import sys
import traceback
import os

import diskio
import wrappers


############################################ executed in parallel processes ###
class FwliteWorker(object):
    """This class is to be subclassed."""
    def __init__(self, name):
        self.name = name
        self.result = wrappers.Wrapper(name=name)

    def node_setup(self, event_handle_wrp):
        pass

    def node_process_event(self, event):
        pass

    def node_finalize(self, event_handle_wrp):
        pass


def _run_workers(event_handle_wrp):
    workers = event_handle_wrp.workers

    # setup workers
    for w in workers:
        try:
            w.node_setup(event_handle_wrp)
        except Exception as e:
            if not isinstance(e, KeyboardInterrupt):
                print '\nin node_setup:'
                traceback.print_exc(file=sys.stdout)
                print event_handle_wrp
                print '\n'
            raise e
        for v in w.result.__dict__.values():
            if isinstance(v, ROOT.TH1):
                v.SetDirectory(0)

    # run the eventloop
    if event_handle_wrp.event_handle.size():
        for event in event_handle_wrp.event_handle:
            for w in workers:
                try:
                    w.node_process_event(event)
                except Exception as e:
                    if not isinstance(e, KeyboardInterrupt):
                        print '\nin node_process_event:'
                        traceback.print_exc(file=sys.stdout)
                        print event_handle_wrp
                        print '\n'
                    raise e

    # finalize workers
    for w in workers:
        try:
            w.node_finalize(event_handle_wrp)
        except Exception as e:
            if not isinstance(e, KeyboardInterrupt):
                print '\nin node_finalize:'
                traceback.print_exc(file=sys.stdout)
                print event_handle_wrp
                print '\n'
            raise e
        if hasattr(event_handle_wrp, 'sample'):
            w.result.sample = event_handle_wrp.sample
            w.result.name = '%s!%s' % (event_handle_wrp.sample, w.result.name)
    del event_handle_wrp.event_handle
    event_handle_wrp.results = list(w.result for w in workers)
    return event_handle_wrp


############################################### executed in control process ###
_proxy = None


def _add_results(event_handle_wrps):
    res_sums = {}
    for evt_hndl_wrp in event_handle_wrps:
        for new_res in evt_hndl_wrp.results:
            if new_res.name in res_sums:
                res_sum = res_sums[new_res.name]
                for k, v in new_res.__dict__.iteritems():
                    if isinstance(v, ROOT.TH1):
                        getattr(res_sum, k).Add(v)
            else:
                res_sums[new_res.name] = diskio.get(new_res.name, new_res)
        if _proxy:
            _proxy.results.update((r, True) for r in res_sums)
            _proxy.files_done[evt_hndl_wrp.filenames[0]] = True
            for res_sum in res_sums.values():
                diskio.write(res_sum, '.cache/' + res_sum.name)
            diskio.write(_proxy, '.cache/' + _proxy.name)
            os.system('mv .cache/* .')

    return res_sums


def work(workers, event_handles=None, use_mp=True):
    global _proxy
    if not event_handles:
        _proxy = diskio.get('fwlite_proxy')
        if not _proxy:
            raise RuntimeError('You must either provide the event_handles '
                               'argument or fwlite_proxy.info in my cwd!')
        if os.path.exists('.cache'):
            os.system('rm .cache/*')
        else:
            os.mkdir('.cache')
        use_mp = _proxy.use_mp

        from DataFormats.FWLite import Events
        def event_handles():
            for sample, files in _proxy.event_files.iteritems():
                for f in files:
                    if f in _proxy.files_done:
                        continue
                    h_evt = Events(f)
                    yield wrappers.Wrapper(
                        event_handle=h_evt,
                        sample=sample,
                        filenames=h_evt._filenames,
                        workers=workers
                    )
    else:
        event_handles = (wrappers.Wrapper(
            event_handle=h_evt,
            filenames=h_evt._filenames
        ) for h_evt in event_handles)

    if use_mp:
        imap_func = multiprocessing.Pool().imap_unordered
    else:
        imap_func = itertools.imap

    results_iter = imap_func(_run_workers, event_handles())
    return _add_results(results_iter)
