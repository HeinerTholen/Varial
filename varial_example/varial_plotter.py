#!/usr/bin/env python

import sys
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gROOT.ProcessLine('gErrorIgnoreLevel = kError;')

if len(sys.argv) < 2:
    print """
Usage:
varial_plotter.py <signal-files>
                  [--bkg <background-files>]
                  [--dat <data-files>]
                  [--psu <pseudodata-files>]

The given files are plotted with these styles:
    - signal files are plotted as lines
    - background files are stacked and plotted as filled histograms
    - data files are plotted as filled circles
    - pseudo-data files are plotted as empty circles

For more control over plotting, a script needs to be implemented.
The varial_plotter.py executable in the /bin directory is probably
the best starting point. Also, check the examples e01 and e02 in
the varial_example module.

Options:
--norm          normalize all input histograms to integral
--rebin         rebin histograms to have a maximum of 42 bins
--filter <p>    plot only histograms with <p> in their in-file-path
"""
    exit(-1)

# grab filenames and options
norm_to_int = False
n_bins_max = 0
sig, bkg, dat, psu, filt = [], [], [], [], []
args = sys.argv[:]
args.pop(0)
current_coll = sig
for a in args:
    if a == '--filter':
        current_coll = filt
    elif a == '--bkg':
        current_coll = bkg
    elif a == '--dat':
        current_coll = dat
    elif a == '--psu':
        current_coll = psu
    elif a == '--norm':
        norm_to_int = True
    elif a == '--rebin':
        n_bins_max = 42
    else:
        current_coll.append(a)
all_input = sig + bkg + dat + psu
filt = filt[0] if filt else ''

print 'signal-files:        ', sig
print 'background-files:    ', bkg
print 'data files:          ', dat
print 'pseudo-data files:   ', psu
if n_bins_max:
    print '- rebinning to a maximum of 42 bins'
if norm_to_int:
    print '- normalizing to integral'
if filt:
    print '- selecting histograms that contain "%s" in their path' % filt


# setup varial
import varial.tools
varial.settings.box_text_size = 0.03
varial.settings.defaults_Legend.update({
    'x_pos': 0.85,
    'y_pos': 0.5,
    'label_width': 0.28,
    'label_height': 0.04,
    'opt': 'f',
    'opt_data': 'p',
    'reverse': True
})
varial.settings.canvas_size_x = 550
varial.settings.canvas_size_y = 400
varial.settings.root_style.SetPadRightMargin(0.3)
varial.settings.rootfile_postfixes = ['.root', '.png']

sample_names = varial.util.setup_legendnames_from_files(all_input)


def label_axes(wrps):
    for w in wrps:
        if 'TH1' in w.type and w.histo.GetXaxis().GetTitle() == '':
            w.histo.GetXaxis().SetTitle(w.histo.GetTitle())
            w.histo.GetYaxis().SetTitle('events')
            w.histo.SetTitle('')
        yield w


# this function processes histograms after loading
def post_load_hook(wrps):
    if n_bins_max:
        wrps = varial.gen.gen_noex_rebin_nbins_max(wrps, n_bins_max)
    wrps = label_axes(wrps)
    wrps = varial.gen.gen_add_wrp_info(
        wrps,
        sample=lambda w: sample_names[w.file_path],
        is_signal=lambda w: w.file_path in sig,
        is_data=lambda w: w.file_path in dat,
        is_pseudo_data=lambda w: w.file_path in psu,
    )
    wrps = sorted(wrps, key=lambda w: w.in_file_path + '__' + w.file_path)
    wrps = varial.gen.gen_make_th2_projections(wrps)
    if norm_to_int:
        wrps = varial.gen.gen_noex_norm_to_integral(wrps)
    return wrps


def plotter_factory(**kws):
    kws['hook_loaded_histos'] = post_load_hook
    kws['save_lin_log_scale'] = True
    kws['stack'] = True
    return varial.tools.Plotter(**kws)


plotter = varial.tools.mk_rootfile_plotter(
    pattern=all_input,
    name='varial_plotter',
    plotter_factory=plotter_factory,
    combine_files=True,
    filter_keyfunc=(lambda w: filt in w.in_file_path) if filt else None,
)


def run():
    varial.tools.Runner(plotter)
    varial.tools.WebCreator().run()
