import ROOT
import itertools
import multiprocessing
import os

import diskio
import wrappers


def _add_results(results_iter):
    res_sums = {}
    for results in results_iter:
        for new_res in results:
            if new_res.name in res_sums:
                res_sum = res_sums[new_res.name]
                for k, v in new_res.__dict__.iteritems():
                    if isinstance(v, ROOT.TH1):
                        getattr(res_sum, k).Add(v)
            else:
                res_sums[new_res.name] = new_res
    return res_sums


def _run_workers(args):
    event_handle_wrp, workers = args
    for w in workers:
        w.node_setup(event_handle_wrp)
    for event in event_handle_wrp.event_handle:
        for w in workers:
            w.node_process_event(event)
    for w in workers:
        w.node_finalize()
        if hasattr(event_handle_wrp, 'sample'):
            w.result.sample = event_handle_wrp.sample
            w.result.name = '%s!%s' % (event_handle_wrp.sample, w.result.name)
    results = list(w.result for w in workers)
    return results


def work(workers, event_handles=None, use_mp=True):
    proxy = None
    if not event_handles:
        if not os.path.exists('fwlite_proxy.info'):
            raise RuntimeError('You must either provide the event_handles '
                               'argument or fwlite_proxy.info in my cwd!')
        proxy = diskio.read('fwlite_proxy')
        use_mp = proxy.__dict__.get('use_mp', use_mp)

        from DataFormats.FWLite import Events
        def event_handles():
            for sample, files in proxy.event_files.iteritems():
                for f in files:
                    h_evt = Events(f)
                    yield wrappers.Wrapper(
                        event_handle=h_evt,
                        sample=sample,
                        filenames=h_evt._filenames,
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
        proxy.results = res.keys()
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
