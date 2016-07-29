"""
Project histograms from trees with map/reduce.
"""


def map_projection(sample_histo_filename, params, open_file=None):
    """Map histogram projection to a root file"""
    from ROOT import TFile, TH1, TH1F, TTree

    sample, histoname, filename = sample_histo_filename.split()
    histoargs = params['histos'][histoname]
    selection = params.get('selection')
    if len(histoargs) == 5:
        quantity, histoargs = histoargs[0], histoargs[1:]
    else:
        quantity = histoname

    if any(isinstance(selection, t) for t in (list, tuple)):
        if params.get('nm1', True):
            # N-1 instruction: don't cut the plotted variable
            selection = list(s for s in selection if quantity not in s)
        selection = ' && '.join(selection)

    selection = '%s*(%s)' % (params.get('weight') or '1', selection or '1')
    histo_draw_cmd = '%s>>+%s' % (quantity, 'new_histo')
    input_file = open_file or TFile(filename)

    try:
        if input_file.IsZombie():
            raise RuntimeError('input_file.IsZombie(): %s' % input_file)

        TH1.AddDirectory(True)
        histo = TH1F('new_histo', *histoargs)

        tree = input_file.Get(params['treename'])
        if not isinstance(tree, TTree):
            raise RuntimeError(
                'There seems to be no tree named "%s" in file "%s"'%(
                    params['treename'], input_file))

        for alias, fcn in params.get('aliases', {}).iteritems():
            if not tree.SetAlias(alias, fcn):
                raise RuntimeError(
                    'Error in TTree::SetAlias: it did not understand %s.'%alias
                )

        n_selected = tree.Draw(histo_draw_cmd, selection, 'goff')
        if n_selected < 0:
            raise RuntimeError(
                'Error in TTree::Project. Are variables, selections and '
                'weights are properly defined? cmd, selection: %s, %s' % (
                    histo_draw_cmd, selection
                )
            )

        histo.SetDirectory(0)
        histo.SetName(histoname)

    finally:
        TH1.AddDirectory(False)
        if not open_file:
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


################################################################## adapters ###
def map_projection_per_file(args):
    sample, filename, params = args
    histos = params['histos'].keys()

    import ROOT
    open_file = ROOT.TFile(filename)
    try:
        map_iter = (res
                    for h in histos
                    for res in map_projection(
                        '%s %s %s'%(sample, h, filename), params, open_file))
        result = list(reduce_projection(map_iter, params))
    finally:
        open_file.Close()

    return result


def reduce_projection_by_two(one, two):
    return list(reduce_projection(one+two, None))


###################################################################### util ###
def store_sample(sample, section, result):
    import varial
    fs_wrp = varial.analysis.fileservice(section)
    fs_wrp.sample = sample
    for sample_histoname, histo in result:
        _, name = sample_histoname.split()
        setattr(fs_wrp, name, histo)
