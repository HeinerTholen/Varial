import glob
import itertools
import os
import shutil
import ROOT

import analysis
import dbio
import diskio
import generators as gen
import rendering
import sample
import settings
import wrappers

from toolinterface import \
    Tool, \
    ToolChain, \
    ToolChainIndie, \
    ToolChainVanilla
from cmsrunproxy import CmsRunProxy
from fwliteproxy import FwliteProxy
from plotter import FSPlotter
from webcreator import WebCreator


class FSHistoLoader(Tool):
    def __init__(self, name=None, filter_keyfunc=None,
                 hook_loaded_histos=None, io=dbio):
        super(FSHistoLoader, self).__init__(name)
        self.filter_keyfunc = filter_keyfunc
        self.hook_loaded_histos = hook_loaded_histos
        self.io = io

    def run(self):
        wrps = gen.fs_filter_active_sort_load(self.filter_keyfunc)
        if self.hook_loaded_histos:
            wrps = self.hook_loaded_histos(wrps)
        self.result = list(wrps)


class CopyTool(Tool):
    """Copy contents of a directory. Preserves .htaccess files."""
    def __init__(self, dest, src='',
                 ignore=("*.root", "*.pdf", "*.eps", "*.log", "*.info"),
                 name=None):
        super(CopyTool, self).__init__(name)
        self.dest = dest
        self.src = src
        self.ignore = ignore

    def run(self):
        src = os.path.abspath(self.src or os.path.join(self.cwd, '..'))
        dest = os.path.abspath(self.dest)

        # check for htaccess and copy it to src dirs
        htaccess = os.path.join(dest, '.htaccess')
        if os.path.exists(htaccess):
            for path, _, _ in os.walk(src):
                shutil.copy2(htaccess, path)

        # clean dest dir and copy
        for f in glob.glob(dest + '/*'):
            shutil.rmtree(f, True)
        ign_pat = shutil.ignore_patterns(*self.ignore)
        for f in glob.glob(src + '/*'):
            if os.path.isdir(f):
                f = os.path.basename(f)
                shutil.copytree(
                    os.path.join(src, f),
                    os.path.join(dest, f),
                    ignore=ign_pat,
                )
            else:
                shutil.copy2(f, dest)


class ZipTool(Tool):
    """Zip-compress a target."""
    def __init__(self, abs_path):
        super(ZipTool, self).__init__(None)
        self.abs_path = abs_path

    def run(self):
        p = os.path.join(settings.varial_working_dir, self.abs_path)
        os.system(
            'zip -r %s %s' % (p, p)
        )


class SampleNormalizer(Tool):
    """Normalize MC cross sections."""
    can_reuse = False

    def __init__(self, filter_lambda, x_range_tuple, name=None):
        super(SampleNormalizer, self).__init__(name)
        self.filter_lambda = filter_lambda
        self.x_range = x_range_tuple

    def get_histos_n_factor(self):
        mcee, data = next(gen.fs_mc_stack_n_data_sum(
            self.filter_lambda
        ))
        dh, mh = data.histo, mcee.histo
        bins = tuple(dh.FindBin(x) for x in self.x_range)
        factor = dh.Integral(*bins) / mh.Integral(*bins)
        canv = next(gen.canvas(
            ((mcee, data),),
            FSPlotter.defaults_attrs['canvas_decorators']
        ))
        return factor, canv

    def run(self):
        # before
        factor, canv = self.get_histos_n_factor()
        next(gen.save_canvas_lin_log([canv], lambda _: 'before'))

        # alter samples
        for s in analysis.mc_samples().itervalues():
            s.lumi /= factor
            s.x_sec /= factor
        for a in analysis.fs_aliases:
            a.lumi /= factor

        # after
        _, canv = self.get_histos_n_factor()
        next(gen.save_canvas_lin_log([canv], lambda _: 'after'))

        self.result = wrappers.FloatWrapper(
            factor,
            name='Lumi factor'
        )


class RootFilePlotter(ToolChain):
    """Plots all histograms in a rootfile."""

    def __init__(self, path=None, name=None):
        super(RootFilePlotter, self).__init__(name)
        ROOT.gROOT.SetBatch()
        if not path:
            path = analysis.cwd + '*.root'
        elif path[-5:] != '.root':
            path += '.root'
        rootfiles = glob.glob(path)
        if not rootfiles:
            self.message('WARNING No rootfile found.')
        else:
            smpl = sample.Sample(
                name='Histogram',
                lumi=1.,
                input_files=rootfiles
            )
            analysis.active_samples = [smpl.name]
            analysis.all_samples = {smpl.name: smpl}
            analysis.fs_aliases = list(itertools.chain.from_iterable(
                diskio.generate_fs_aliases(f, smpl) for f in rootfiles
            ))
            plotters = list(FSPlotter(
                filter_keyfunc=lambda w: w.file_path.split('/')[-1] == f,
                name='Plotter_'+f[:-5]
            ) for f in rootfiles)
            self.add_tool(ToolChain(self.name, plotters))


