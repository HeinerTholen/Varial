from ROOT import TH1D
import math


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
