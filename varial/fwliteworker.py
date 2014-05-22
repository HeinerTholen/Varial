import ROOT
import itertools
import multiprocessing
import os

import diskio
import wrappers


def _add_results(results_iter):
    res_sums = {}
    for results in results_iter:
        if not res_sums:
            res_sums = dict((r.name, r) for r in results)
        else:
            for res in results:
                res_sum = res_sums[res.name]
                for k, v in res.__dict__.iteritems():
                    if isinstance(v, ROOT.TH1):
                        getattr(res_sum, k).Add(v)
    return res_sums


def _run_workers(args):
    event_handle, workers = args
    for w in workers:
        w.node_setup(event_handle)
    for event in event_handle:
        for w in workers:
            w.node_process_event(event)
    for w in workers:
        w.node_finalize()
    results = list(w.result for w in workers)
    return results


def work(workers, event_handles=None, use_mp=True):

    proxy = None
    if not event_handles:
        if not os.path.exists('fwlite_proxy.info'):
            raise RuntimeError('You must either provide the event_handles '
                               'argument or the proxy.json in my cwd!')
        proxy = diskio.read('fwlite_proxy')
        from DataFormats.FWLite import Events
        event_handles = (Events(f) for f in proxy.event_files)
        use_mp = proxy.__dict__.get('use_mp', use_mp)

    if use_mp:
        imap_func = multiprocessing.Pool().imap_unordered
    else:
        imap_func = itertools.imap

    results_iter = imap_func(
        _run_workers,
        itertools.izip(
            event_handles,
            itertools.repeat(workers),
        )
    )
    res = _add_results(results_iter)
    if proxy:
        for r in res.values():
            diskio.write(r)
        proxy.results = list(w.name for w in res)
        diskio.write(proxy)
    return res


class FwliteWorker(object):
    """This class is to be subclassed."""
    def __init__(self, name):
        self.name = name
        self.result = wrappers.Wrapper(name)

    def node_setup(self, event_handle):
        pass

    def node_process_event(self, event):
        pass

    def node_finalize(self):
        pass
