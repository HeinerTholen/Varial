import functools
import itertools
import inspect
import ctypes
import random
import ROOT
import copy
import math
import os


def integral_and_error(th_hist):
    err = ctypes.c_double()
    if isinstance(th_hist, ROOT.TH2):
        val = th_hist.IntegralAndError(
            0, th_hist.GetNbinsX(), 0, th_hist.GetNbinsY(), err)
    else:
        val = th_hist.IntegralAndError(0, th_hist.GetNbinsX(), err)
    return round(val, 1), round(err.value, 1)


def integral_and_corr_error(th_hist):
    ntgrl = th_hist.Integral()
    err_sum = sum(
        th_hist.GetBinError(i+1)
        for i in xrange(
            th_hist.GetBin(
                th_hist.GetNbinsX(), th_hist.GetNbinsY(), th_hist.GetNbinsZ()))
    )
    return round(ntgrl, 1), round(err_sum, 1)


def random_hex_str():
    return hex(random.randint(0, 1e10))[-7:]


def project_items(keyfunc, items):
    positive = list(itertools.ifilter(keyfunc, items))
    negative = list(itertools.ifilterfalse(keyfunc, items))
    return positive, negative


def list2histogram(values, name='histo', title=None, n_bins=0):
    """Makes histogram from list of values."""
    mi, ma = min(values), max(values)
    val_range = ma - mi
    bounds = mi - 0.1*val_range, ma + 0.1*val_range
    if n_bins:
        n_bins = int(n_bins)
    else:
        n_bins = list2nbins_scott(values)

    if not title:
        title = name
    histo = ROOT.TH1D(name, title, n_bins, *bounds)
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
    ):
        return obj
    if isinstance(obj, list):
        return list(deepish_copy(o) for o in obj)
    if isinstance(obj, tuple):
        return tuple(deepish_copy(o) for o in obj)
    if isinstance(obj, dict):
        return dict((k, deepish_copy(v)) for k, v in obj.iteritems())
    if isinstance(obj, set):
        return set(deepish_copy(o) for o in obj)
    if hasattr(obj, '__dict__'):
        cp = copy.copy(obj)
        cp.__dict__.clear()
        for k, v in obj.__dict__.iteritems():
            cp.__dict__[k] = deepish_copy(v)
        return cp
    return obj


def setup_legendnames_from_files(pattern):
    import generators as gen  # hide circular dependency
    filenames = gen.resolve_file_pattern(pattern)

    # try the sframe way:
    lns = list(n.split('.') for n in filenames if isinstance(n, str))
    if all(len(l) == 5 for l in lns):
        res = dict((f, l[3]) for f, l in itertools.izip(filenames, lns))

        # make sure the legend names are all different
        if len(set(l for l in res.itervalues())) == len(res):
            return res

    # not sframe but only one file: return
    if len(filenames) < 2:
        return {os.path.basename(filenames[0]): filenames[0]}

    # try trim filesnames from front and back
    lns = list(os.path.splitext(f)[0] for f in filenames)
    # shorten strings from front
    while all(n[0] == lns[0][0] and len(n) > 5 for n in lns):
        for i in xrange(len(lns)):
            lns[i] = lns[i][1:]

    # shorten strings from back
    while all(n[-1] == lns[0][-1] and len(n) > 5 for n in lns):
        for i in xrange(len(lns)):
            lns[i] = lns[i][:-1]
    return dict((f, l) for f, l in itertools.izip(filenames, lns))


#################################################################### Switch ###
class Switch(object):
    """Set variables only within a context."""

    def __init__(self, obj, var_name, new_val):
        assert(type(var_name) == str)
        self.obj = obj
        self.var_name = var_name
        self.new_val = new_val
        self.old_val = None

    def __enter__(self):
        self.old_val = getattr(self.obj, self.var_name)
        setattr(self.obj,self.var_name, self.new_val)

    def __exit__(self, exc_type, exc_val, exc_tb):
        setattr(self.obj, self.var_name, self.old_val)
        return exc_type, exc_val, exc_tb


############################################################ ResettableType ###
_instance_init_states = {}


def _wrap_init(original__init__):
    @functools.wraps(original__init__)
    def init_hook(inst, *args, **kws):
        if inst not in _instance_init_states:
            _instance_init_states[inst] = None
            res = original__init__(inst, *args, **kws)
            if inst.no_reset:
                del _instance_init_states[inst]
                return res
            else:
                _instance_init_states[inst] = deepish_copy(inst.__dict__)
                return res
        else:
            return original__init__(inst, *args, **kws)
    return init_hook


def _reset(inst):
    if not inst.no_reset:
        inst.__dict__.clear()
        inst.__dict__.update(
            deepish_copy(_instance_init_states[inst])
        )


def _update_init_state(inst):
    if not inst.no_reset:
        _instance_init_states[inst] = deepish_copy(inst.__dict__)


class ResettableType(type):
    """
    Wraps __init__ to store object _after_ init.

    >>> class Foo(object):
    ...     __metaclass__ = ResettableType
    ...     def __init__(self):
    ...         self.bar = 'A'
    >>> foo = Foo()
    >>> foo.bar = 'B'
    >>> foo.reset()
    >>> foo.bar
    'A'
    """
    def __new__(mcs, *more):
        mcs = super(ResettableType, mcs).__new__(mcs, *more)
        mcs.__init__ = _wrap_init(mcs.__init__)
        mcs.reset = _reset
        mcs.update = _update_init_state
        return mcs


if __name__ == '__main__':
    import doctest
    doctest.testmod()
