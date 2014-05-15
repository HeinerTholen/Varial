import ROOT
import itertools
import hashlib
import random
import multiprocessing
import os

import diskio


def _add_results(results_iter):
    res_sums = []
    for results in results_iter:
        if not res_sums:
            for res in results:
                wrp = diskio.read(res)
                wrp.name = wrp.name.split("_&&&_")[1]
                res_sums.append(wrp)
        else:
            for res, res_sum in zip(results, res_sums):
                wrp = diskio.read(res)
                for k, v in wrp.__dict__.iteritems():
                    if isinstance(v, ROOT.TH1):
                        getattr(res_sum, k).Add(v)
        for res in results:
            os.remove("%s.info" % res)
            os.remove("%s.root" % res)
    for r in res_sums:
        diskio.write(r)
    return res_sums


def _start_workers(args):
    event_handle, workers = args
    for w in workers:
        w.node_setup()
    for event in event_handle:
        for w in workers:
            w.node_process_event(event)
    results = list(
        w.node_finalize() for w in workers
    )
    return results


def start_work(workers, event_handles):
    pool = multiprocessing.Pool()
    results_iter = pool.imap_unordered(
        _start_workers,
        zip(
            event_handles,
            itertools.repeat(workers),
        )
    )
    _add_results(results_iter)


class FwliteWorker(object):
    def __init__(self, name):
        self.result = diskio.fileservice(name, False)

    def node_setup(self):
        pass

    def node_process_event(self, event):
        pass

    def node_finalize(self):
        self.result.name = "%s_&&&_%s" % (
            hashlib.sha1(str(random.random())).hexdigest(), self.result.name
        )
        diskio.write(self.result)
        return self.result.name


