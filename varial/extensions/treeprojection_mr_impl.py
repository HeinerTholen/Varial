"""
Project histograms from trees in the style of map/reduce.

Implementation ready for disco map/reduce framework as well as jug.
"""


def map_projection(sample_histo_filename, params):
    """Map histogram projections to a root file"""

    import ROOT
    sample, histoname, filename = sample_histo_filename.split()
    input_file = ROOT.TFile(filename)

    try:
        ROOT.TH1.AddDirectory(True)
        tree = input_file.Get(params['treename'])

        nm1 = params.get('nm1', True)
        selection = params.get('selection') or '1'
        weight = params.get('weight') or '1'
        if nm1 and histoname in selection:  # N-1 instruction
            sel = weight
        else:
            sel = '%s*(%s)' % (weight, selection)

        histoargs = params['histos'][histoname]
        histo = ROOT.TH1F(histoname, *histoargs)
        n_sel = tree.Project(histoname, histoname, sel)
        if n_sel < 0:
            raise RuntimeError('Error in TTree::Project. Are variables, '
                               'selections and weights are properly defined? '
                               'Please check logs.')
        histo.SetDirectory(0)

    finally:
        ROOT.TH1.AddDirectory(False)
        input_file.Close()

    yield sample+' '+histoname, histo


def reduce_projection(iterator, params):
    """Reduce by sample and add containers."""

    def _kvgroup(it):  # returns iterator over (key, [val1, val2, ...])
        from itertools import groupby
        for k, kvs in groupby(it, lambda kv: kv[0]):
            yield k, (v for _, v in kvs)

    def _histo_sum(h_iter):  # returns single histogram
        h_sum = next(h_iter).Clone()
        for h in h_iter:
            h_sum.Add(h)
        return h_sum

    for sample_histo, histos in _kvgroup(sorted(iterator)):
        yield sample_histo, _histo_sum(histos)


####################################################################### jug ###
def jug_map_projection_per_file(args):
    sample, histos, filename, params = args

    map_iter = (res
                for h in histos
                for res in map_projection(
                    '%s %s %s'%(sample, h, filename), params))
    result = reduce_projection(map_iter, params)

    return list(result)


def jug_reduce_projection(one, two):
    return list(reduce_projection(one+two, None))
