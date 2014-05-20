import copy
import inspect
import math
from ROOT import TH1D


def list2histogram(values, name="histo", title=None, n_bins=0):
    """Makes histogram from list of values."""
    mi, ma, n = min(values), max(values), len(values)
    val_range = ma - mi
    bounds = mi - 0.1*val_range, ma + 0.1*val_range
    if n_bins:
        n_bins = int(n_bins)
    else:
        n_bins = list2nbins_scott(values)

    if not title:
        title = name
    histo = TH1D(name, title, n_bins, *bounds)
    for v in values:
        histo.Fill(v)
    return histo


def list2nbins_scott(values):
    """
    Taken from equation (3) in
    http://arxiv.org/abs/physics/0605197
    """
    mi, ma, n = min(values), max(values), len(values)
    val_range = ma - mi
    mean = sum(values) / n
    var = sum((v-mean)**2 for v in values) / n
    return int(math.ceil(val_range * n**.333 / 3.49 / var))


def deepish_copy(obj):
    if (
        isinstance(obj, type)
        or callable(obj)
        or inspect.ismodule(obj)
        or inspect.isclass(obj)
        #or str(type(obj)) == "<type 'generator'>"
    ):
        return obj
    if type(obj) == list:
        return list(deepish_copy(o) for o in obj)
    if type(obj) == tuple:
        return tuple(deepish_copy(o) for o in obj)
    if type(obj) == dict:
        return dict((k, deepish_copy(v)) for k, v in obj.iteritems())
    if type(obj) == set:
        return set(deepish_copy(o) for o in obj)
    if hasattr(obj, "__dict__"):
        cp = copy.copy(obj)
        cp.__dict__.clear()
        for k, v in obj.__dict__.iteritems():
            cp.__dict__[k] = deepish_copy(v)
        return cp
    return obj















