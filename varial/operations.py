"""
Operations on wrappers
"""

import array
import __builtin__
import ctypes
import collections
from ROOT import THStack

import history
import wrappers


class OperationError(Exception): pass
class TooFewWrpsError(OperationError): pass
class TooManyWrpsError(OperationError): pass
class WrongInputError(OperationError): pass
class NoLumiMatchError(OperationError): pass


def iterableize(obj):
    if isinstance(obj, collections.Iterable):
        return obj
    else:
        return [obj]


@history.track_history
def stack(wrps):
    """
    Applies only to HistoWrappers. Returns StackWrapper.
    Checks lumi to be equal among all wrappers.

    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 4.5)
    >>> h1.Fill(1,4)
    1
    >>> w1 = wrappers.HistoWrapper(h1, lumi=2.)
    >>> h2 = TH1I("h2", "", 2, .5, 4.5)
    >>> h2.Fill(1,3)
    1
    >>> h2.Fill(3,6)
    2
    >>> w2 = wrappers.HistoWrapper(h2, lumi=2.)
    >>> w3 = stack([w1, w2])
    >>> w3.histo.Integral()
    13.0
    >>> w3.lumi
    2.0
    """
    wrps    = iterableize(wrps)
    stk_wrp = None
    lumi    = 0.
    info    = None
    sample  = ""
    for wrp in wrps:
        if not isinstance(wrp, wrappers.HistoWrapper):          # histo check
            raise WrongInputError(
                "stack accepts only HistoWrappers. wrp: "
                + str(wrp)
            )
        if not stk_wrp:                                         # stack init
            stk_wrp = THStack(wrp.name, wrp.title)
            lumi = wrp.lumi
            info = wrp.all_info()
            sample = wrp.sample
        elif lumi != wrp.lumi:                                  # lumi check
            raise NoLumiMatchError(
                "stack needs lumis to match. (%f != %f)" % (lumi, wrp.lumi)
            )
        if sample != wrp.sample:                                # add to stack
            sample = ""
        stk_wrp.Add(wrp.histo)
    if not info:
        raise TooFewWrpsError(
            "At least one Wrapper must be provided."
        )
    if not sample:
        del info["sample"]
    return wrappers.StackWrapper(stk_wrp, **info)


@history.track_history
def sum(wrps):
    """
    Applies only to HistoWrappers. Returns HistoWrapper. Adds lumi up.
    
    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 4.5)
    >>> h1.Fill(1)
    1
    >>> w1 = wrappers.HistoWrapper(h1, lumi=2.)
    >>> h2 = TH1I("h2", "", 2, .5, 4.5)
    >>> h2.Fill(1)
    1
    >>> h2.Fill(3)
    2
    >>> w2 = wrappers.HistoWrapper(h2, lumi=3.)
    >>> w3 = sum([w1, w2])
    >>> w3.histo.Integral()
    3.0
    >>> w3.lumi
    5.0
    """
    wrps = iterableize(wrps)
    histo = None
    lumi = 0.
    info = None
    for wrp in wrps:
        if not isinstance(wrp, wrappers.HistoWrapper):
            raise WrongInputError(
                "sum accepts only HistoWrappers. wrp: "
                + str(wrp)
            )
        if histo:
            histo.Add(wrp.histo)
        else:
            histo = wrp.histo.Clone()
            info = wrp.all_info()
        lumi += wrp.lumi
    if not info:
        raise TooFewWrpsError(
            "At least one Wrapper must be provided."
        )
    info["lumi"] = lumi
    return wrappers.HistoWrapper(histo, **info)


@history.track_history
def merge(wrps):
    """
    Applies only to HistoWrapper. Returns HistoWrapper. Normalizes histos to lumi.

    >>> from ROOT import TH1I    
    >>> h1 = TH1I("h1", "", 2, .5, 2.5)
    >>> h1.Fill(1,4)
    1
    >>> w1 = wrappers.HistoWrapper(h1, lumi=2.)
    >>> h2 = TH1I("h2", "", 2, .5, 2.5)
    >>> h2.Fill(1,3)
    1
    >>> h2.Fill(2,6)
    2
    >>> w2 = wrappers.HistoWrapper(h2, lumi=3.)
    >>> w3 = merge([w1, w2])
    >>> w3.histo.Integral()
    5.0
    >>> w3.lumi
    1.0
    """
    wrps = iterableize(wrps)
    histo = None
    info = None
    for wrp in wrps:
        if not isinstance(wrp, wrappers.HistoWrapper):
            raise WrongInputError(
                "merge accepts only HistoWrappers. wrp: "
                + str(wrp)
            )
        if histo:
            histo.Add(wrp.histo, 1. / wrp.lumi)
        else:
            histo = wrp.histo.Clone()
            histo.Scale(1. / wrp.lumi)
            info = wrp.all_info()
    if not info:
        raise TooFewWrpsError(
            "At least one Wrapper must be provided."
        )
    info["lumi"] = 1.
    return wrappers.HistoWrapper(histo, **info)


@history.track_history
def prod(wrps):
    """
    Applies to HistoWrapper and FloatWrapper. Returns HistoWrapper. Takes lumi from first.
    
    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 2.5)
    >>> h1.Fill(1)
    1
    >>> w1 = wrappers.HistoWrapper(h1, lumi=2, history="w1")
    >>> h2 = TH1I("h2", "", 2, .5, 2.5)
    >>> h2.Fill(1)
    1
    >>> h2.Fill(2)
    2
    >>> w2 = wrappers.HistoWrapper(h2, lumi=3)
    >>> w3 = prod([w1, w2])
    >>> w3.histo.Integral()
    1.0
    >>> w3.lumi
    1.0
    >>> w4 = wrappers.FloatWrapper(2.)
    >>> w5 = prod([w1, w4])
    >>> w5.histo.Integral()
    2.0
    """
    wrps = iterableize(wrps)
    histo = None
    info = None
    lumi = 1.
    for wrp in wrps:
        if histo:
            if isinstance(wrp, wrappers.HistoWrapper):
                histo.Multiply(wrp.histo)
                lumi = 1.
            elif not isinstance(wrp, wrappers.FloatWrapper):
                raise WrongInputError(
                    "prod accepts only HistoWrappers and FloatWrappers. wrp: "
                    + str(wrp)
                )
            else:
                histo.Scale(wrp.float)
                lumi *= wrp.float
        else:
            if not isinstance(wrp, wrappers.HistoWrapper):
                raise WrongInputError(
                    "prod expects first argument to be of type HistoWrapper. wrp: "
                    + str(wrp)
                )
            histo = wrp.histo.Clone()
            info = wrp.all_info()
            lumi = wrp.lumi
    if not info:
        raise TooFewWrpsError(
            "At least one Wrapper must be provided."
        )
    info["lumi"] = lumi
    return wrappers.HistoWrapper(histo, **info)


@history.track_history
def div(wrps):
    """
    Applies to HistoWrapper and FloatWrapper. Returns HistoWrapper. Takes lumi from first.
    
    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 2.5)
    >>> h1.Fill(1,4)
    1
    >>> w1 = wrappers.HistoWrapper(h1, lumi=2)
    >>> h2 = TH1I("h2", "", 2, .5, 2.5)
    >>> h2.Fill(1,2)
    1
    >>> w2 = wrappers.HistoWrapper(h2, lumi=3)
    >>> w3 = div([w1, w2])
    >>> w3.histo.Integral()
    2.0
    >>> w4 = wrappers.FloatWrapper(2., history="w4")
    >>> w5 = div([w1, w4])
    >>> w5.histo.Integral()
    2.0
    """
    wrps = iterableize(wrps)
    wrps = iter(wrps)
    try:
        nominator = next(wrps)
        denominator = next(wrps)
    except StopIteration:
        raise TooFewWrpsError("div needs exactly two Wrappers.")
    try:
        wrps.next()
        raise TooManyWrpsError("div needs exactly two Wrappers.")
    except StopIteration:
        pass
    if not isinstance(nominator, wrappers.HistoWrapper):
        raise WrongInputError(
            "div needs nominator to be of type HistoWrapper. nominator: "
            + str(nominator)
        )
    if not (isinstance(denominator, wrappers.HistoWrapper) or
            isinstance(denominator, wrappers.FloatWrapper)):
        raise WrongInputError(
            "div needs denominator to be of type HistoWrapper or FloatWrapper. denominator: "
            + str(denominator)
        )

    histo = nominator.histo.Clone()
    lumi = nominator.lumi
    if isinstance(denominator, wrappers.HistoWrapper):
        histo.Divide(denominator.histo)
        lumi = 1.
    else:
        histo.Scale(1. / denominator.float)
        lumi /= denominator.float
    info = nominator.all_info()
    info["lumi"] = lumi
    return wrappers.HistoWrapper(histo, **info)


@history.track_history
def lumi(wrp):
    """
    Applies to HistoWrapper. Returns FloatWrapper.
    
    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 2.5)
    >>> h1.Fill(1)
    1
    >>> w1 = wrappers.HistoWrapper(h1, lumi=2.)
    >>> w2 = lumi(w1)
    >>> w2.float
    2.0
    """
    if not isinstance(wrp, wrappers.HistoWrapper):
        raise WrongInputError(
            "lumi needs argument of type HistoWrapper. histo: "
            + str(wrp)
        )

    info = wrp.all_info()
    return wrappers.FloatWrapper(wrp.lumi, **info)


@history.track_history
def norm_to_lumi(wrp):
    """
    Applies to HistoWrapper. Returns HistoWrapper.
    
    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 2.5)
    >>> h1.Fill(1, 4)
    1
    >>> w1 = wrappers.HistoWrapper(h1, lumi=2.)
    >>> w1.histo.Integral()
    4.0
    >>> w2 = norm_to_lumi(w1)
    >>> w2.histo.Integral()
    2.0
    """
    if not isinstance(wrp, wrappers.HistoWrapper):
        raise WrongInputError(
            "norm_to_lumi needs argument of type HistoWrapper. histo: "
            + str(wrp)
        )
    histo = wrp.histo.Clone()
    histo.Scale(1. / wrp.lumi)
    info = wrp.all_info()
    info["lumi"] = 1.
    return wrappers.HistoWrapper(histo, **info)


@history.track_history
def norm_to_integral(wrp, use_bin_width=False):
    """
    Applies to HistoWrapper. Returns HistoWrapper.
    
    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 2.5)
    >>> h1.Fill(1, 4)
    1
    >>> w1 = wrappers.HistoWrapper(h1, lumi=2.)
    >>> w1.histo.Integral()
    4.0
    >>> w2 = norm_to_integral(w1)
    >>> w2.histo.Integral()
    1.0
    """
    if not isinstance(wrp, wrappers.HistoWrapper):
        raise WrongInputError(
            "norm_to_integral needs argument of type HistoWrapper. histo: "
            + str(wrp)
        )
    histo = wrp.histo.Clone()
    option = "width" if use_bin_width else ""
    integr = wrp.histo.Integral(option)
    histo.Scale(1. / integr)
    info = wrp.all_info()
    info["lumi"] /= integr
    return wrappers.HistoWrapper(histo, **info)


@history.track_history
def copy(wrp):
    """
    Applies to HistoWrapper. Returns HistoWrapper.
    
    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 2.5)
    >>> h1.Fill(1, 4)
    1
    >>> w1 = wrappers.HistoWrapper(h1, lumi=2.)
    >>> w2=copy(w1)
    >>> w2.histo.GetName()
    'h1'
    >>> w1.name == w2.name
    True
    >>> w1.histo.Integral() == w2.histo.Integral()
    True
    >>> w1.histo != w2.histo
    True
    """
    if not isinstance(wrp, wrappers.HistoWrapper):
        raise WrongInputError(
            "copy needs argument of type HistoWrapper. histo: "
            + str(wrp)
        )
    histo = wrp.histo.Clone()
    info = wrp.all_info()
    return wrappers.HistoWrapper(histo, **info)


@history.track_history
def rebin(wrp, bin_bounds, norm_by_bin_width=False):
    """
    Applies to HistoWrapper. Returns Histowrapper.

    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 4, .5, 4.5)
    >>> h1.Fill(1)
    1
    >>> h1.Fill(2)
    2
    >>> w1 = wrappers.HistoWrapper(h1, lumi=2.)
    >>> w2=rebin(w1, [.5, 2.5, 4.5])
    >>> w1.histo.GetNbinsX()
    4
    >>> w2.histo.GetNbinsX()
    2
    >>> w2.histo.GetBinContent(1)
    2.0
    >>> w2.histo.GetBinContent(2)
    0.0
    """
    if not isinstance(wrp, wrappers.HistoWrapper):
        raise WrongInputError(
            "rebin needs argument of type HistoWrapper. histo: "
            + str(wrp)
        )
    if len(bin_bounds) < 2:
        raise OperationError(
            "Number of bins < 2, must include at least one bin!"
        )
    bin_bounds = array.array("d", bin_bounds)
    orig_bin_width = wrp.histo.GetBinWidth(1)
    histo = wrp.histo.Rebin(
        len(bin_bounds) - 1,
        wrp.name,
        bin_bounds
    )
    if norm_by_bin_width:
        for i in xrange(histo.GetNbinsX()+1):
            factor = histo.GetBinWidth(i) / orig_bin_width
            histo.SetBinContent(i, histo.GetBinContent(i) / factor)
            histo.SetBinError(i, histo.GetBinError(i) / factor)
    info = wrp.all_info()
    return wrappers.HistoWrapper(histo, **info)


@history.track_history
def trim(wrp, left=True, right=True):
    """
    Applies to HistoWrapper. Returns Histowrapper.

    If left / right are set to values, these are applied. Otherwise empty bins
    are cut off.

    >>> from ROOT import TH1I
    >>> w1 = wrappers.HistoWrapper(TH1I("h1", "", 10, .5, 10.5))
    >>> w1.histo.Fill(5)
    5
    >>> w2 = trim(w1)
    >>> w2.histo.GetNbinsX()
    1
    >>> w2.histo.GetXaxis().GetXmin()
    4.5
    >>> w2.histo.GetXaxis().GetXmax()
    5.5
    >>> w2 = trim(w1, 3.5, 7.5)
    >>> w2.histo.GetNbinsX()
    4
    >>> w2.histo.GetXaxis().GetXmin()
    3.5
    >>> w2.histo.GetXaxis().GetXmax()
    7.5
    """
    if not isinstance(wrp, wrappers.HistoWrapper):
        raise WrongInputError(
            "trim needs argument of type HistoWrapper. histo: "
            + str(wrp)
        )

    # find left / right values if not given
    histo = wrp.histo
    axis = histo.GetXaxis()
    n_bins = histo.GetNbinsX()
    if type(left) == bool:
        if left:
            for i in xrange(n_bins+1):
                if histo.GetBinContent(i):
                    left = axis.GetBinLowEdge(i)
                    break
        else:
            left = axis.GetXmin()
    if type(right) == bool:
        if right:
            for i in xrange(n_bins+1, 0, -1):
                if histo.GetBinContent(i):
                    right = axis.GetBinUpEdge(i)
                    break
        else:
            right = axis.GetXmax()
    if left > right:
        raise OperationError("bounds: left > right")

    # create new bin_bounds
    index = 0
    while axis.GetBinLowEdge(index) < left:
        index += 1
    bin_bounds = [axis.GetBinLowEdge(index)]
    while axis.GetBinUpEdge(index) <= right:
        bin_bounds.append(axis.GetBinUpEdge(index))
        index += 1

    return rebin(wrp, bin_bounds)


@history.track_history
def mv_in(wrp, overflow=True, underflow=True):
    """
    Moves under- and/or overflow bin into first/last bin.

    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 4.5)
    >>> h1.Fill(0)
    -1
    >>> h1.Fill(5,3)
    -1
    >>> w1 = wrappers.HistoWrapper(h1)
    >>> w1.histo.Integral()
    0.0
    >>> w2 = mv_in(w1, False, False)
    >>> w2.histo.Integral()
    0.0
    >>> w3 = mv_in(w1, True, False)
    >>> w3.histo.Integral()
    3.0
    >>> w4 = mv_in(w1, False, True)
    >>> w4.histo.Integral()
    1.0
    >>> w5 = mv_in(w1, True, True)
    >>> w5.histo.Integral()
    4.0
    """
    if not isinstance(wrp, wrappers.HistoWrapper):
        raise WrongInputError(
            "mv_bin needs argument of type HistoWrapper. histo: "
            + str(wrp)
        )
    histo = wrp.histo.Clone()
    nbins     = histo.GetNbinsX()
    if underflow:
        firstbin  = histo.GetBinContent(0)
        firstbin += histo.GetBinContent(1)
        histo.SetBinContent(1, firstbin)
        histo.SetBinContent(0, 0.)
    if overflow:
        lastbin   = histo.GetBinContent(nbins + 1)
        lastbin  += histo.GetBinContent(nbins)
        histo.SetBinContent(nbins, lastbin)
        histo.SetBinContent(histo.GetNbinsX() + 1, 0.)
    return wrappers.HistoWrapper(histo, **wrp.all_info())


@history.track_history
def integral(wrp, use_bin_width=False):
    """
    Integral. Applies to HistoWrapper. Returns FloatWrapper.
    
    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 4.5)
    >>> h1.Fill(1)
    1
    >>> h1.Fill(3,3)
    2
    >>> w1 = wrappers.HistoWrapper(h1)
    >>> w2 = integral(w1)
    >>> w2.float
    4.0
    >>> w3 = integral(w1, True)
    >>> w3.float
    8.0
    """
    if not isinstance(wrp, wrappers.HistoWrapper):
        raise WrongInputError(
            "int needs argument of type HistoWrapper. histo: "
            + str(wrp)
        )
    option = "width" if use_bin_width else ""
    info = wrp.all_info()
    return wrappers.FloatWrapper(wrp.histo.Integral(option), **info)


@history.track_history
def int_l(wrp, use_bin_width=False):
    """
    Left-sided integral. Applies to HistoWrapper. Returns HistoWrapper.
    
    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 4.5)
    >>> h1.Fill(1)
    1
    >>> h1.Fill(3,2)
    2
    >>> w1 = wrappers.HistoWrapper(h1)
    >>> w2 = int_l(w1)
    >>> w2.histo.GetBinContent(1)
    1.0
    >>> w2.histo.GetBinContent(2)
    3.0
    >>> w2 = int_l(w1, True)
    >>> w2.histo.GetBinContent(1)
    2.0
    >>> w2.histo.GetBinContent(2)
    6.0
    """
    if not isinstance(wrp, wrappers.HistoWrapper):
        raise WrongInputError(
            "int_l needs argument of type HistoWrapper. histo: "
            + str(wrp)
        )
    int_histo = wrp.histo.Clone()
    option = "width" if use_bin_width else ""
    for i in xrange(int_histo.GetNbinsX(), 0, -1):
        error = ctypes.c_double()
        value = int_histo.IntegralAndError(1, i, error, option)
        int_histo.SetBinContent(i, value)
        int_histo.SetBinError(i, error.value)
    info = wrp.all_info()
    return wrappers.HistoWrapper(int_histo, **info)


@history.track_history
def int_r(wrp, use_bin_width=False):
    """
    Applies to HistoWrapper. Returns HistoWrapper.
    
    >>> from ROOT import TH1I
    >>> h1 = TH1I("h1", "", 2, .5, 4.5)
    >>> h1.Fill(1)
    1
    >>> h1.Fill(3,2)
    2
    >>> w1 = wrappers.HistoWrapper(h1)
    >>> w2 = int_r(w1)
    >>> w2.histo.GetBinContent(1)
    3.0
    >>> w2.histo.GetBinContent(2)
    2.0
    >>> w2 = int_r(w1, True)
    >>> w2.histo.GetBinContent(1)
    6.0
    >>> w2.histo.GetBinContent(2)
    4.0
    """
    if not isinstance(wrp, wrappers.HistoWrapper):
        raise WrongInputError(
            "int_r needs argument of type HistoWrapper. histo: "
            + str(wrp)
        )
    int_histo = wrp.histo.Clone()
    option = "width" if use_bin_width else ""
    n_bins = int_histo.GetNbinsX()
    for i in xrange(1, 1 + n_bins):
        error = ctypes.c_double()
        value = int_histo.IntegralAndError(i, n_bins, error, option)
        int_histo.SetBinContent(i, value)
        int_histo.SetBinError(i, error.value)
    info = wrp.all_info()
    return wrappers.HistoWrapper(int_histo, **info)


@history.track_history
def chi2(wrps, x_min=0, x_max=0):
    """
    Expects two Histowrappers. Returns FloatWrapper.
    """
    wrps = iterableize(wrps)
    wrps = iter(wrps)
    try:
        first, second = next(wrps), next(wrps)
    except StopIteration:
        raise TooFewWrpsError("chi2 needs exactly two HistoWrappers.")
    try:
        wrps.next()
        raise TooManyWrpsError("chi2 needs exactly two HistoWrappers.")
    except StopIteration:
        pass
    for w in (first, second):
        if not isinstance(w, wrappers.HistoWrapper):
            raise WrongInputError(
                "chi2 needs type HistoWrapper. w: "
                + str(w)
            )
    if not first.histo.GetNbinsX() == second.histo.GetNbinsX():
        raise WrongInputError(
            "chi2 needs histos with same number of bins."
        )
    if not x_max:
        x_max = int(first.histo.GetNbinsX() - 1)

    def get_weight_for_bin(i):
        val = (first.histo.GetBinContent(i+1)
               - second.histo.GetBinContent(i+1))**2
        err1 = first.histo.GetBinError(i+1)
        err2 = second.histo.GetBinError(i+1)
        if err1 and err2:
            return val / (err1**2 + err2**2)
        else:
            return 0.

    chi2_val = __builtin__.sum(
        get_weight_for_bin(i)
        for i in xrange(x_min, x_max)
    )
    info = second.all_info()
    info.update(first.all_info())
    return wrappers.FloatWrapper(
        chi2_val,
        **info
    )


if __name__ == "__main__":
    import doctest
    doctest.testmod()
