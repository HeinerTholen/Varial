"""
Project histograms from trees in the style of map/reduce.

Implementation ready for disco map/reduce framework.
"""


def map_projection(sample_histo_filename, params):
    """Map histogram projections to a root file"""
    sample, histoname, filename = sample_histo_filename.split()

    import ROOT
    ROOT.gROOT.SetBatch(True)
    input_file = ROOT.TFile(filename)

    try:
        ROOT.TH1.AddDirectory(True)
        tree = input_file.Get(params['treename'])

        nm1 = params.get('nm1', True)
        selection = params.get('selection', '')
        weight = params.get('weight', '1.')
        if nm1 and histoname in selection:  # N-1 instruction
            sel = weight
        else:
            sel = '%s*(%s)' % (weight, selection)

        histoargs = params['histos'][histoname]
        histo = ROOT.TH1F(histoname, *histoargs)
        tree.Project(histoname, histoname, sel)
        histo.SetDirectory(0)

    finally:
        ROOT.TH1.AddDirectory(False)
        input_file.Close()

    yield sample+' '+histoname, histo


def reduce_projection(iter, params):
    """Reduce by sample and add containers."""

    def _key(k_v):  # need function, no lambdas allowed
        return k_v[0]

    def _kvgroup(it):  # returns iterator over (key, [val1, val2, ...])
        from itertools import groupby
        for k, kvs in groupby(it, _key):
            yield k, (v for _, v in kvs)

    def _histo_sum(h_iter):  # returns single histogram
        h_sum = next(h_iter).Clone()
        for h in h_iter:
            h_sum.Add(h)
        return h_sum

    for sample_histo, histos in _kvgroup(sorted(iter)):
        yield sample_histo, _histo_sum(histos)


################################################################### utility ###
