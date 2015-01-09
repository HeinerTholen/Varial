"""
All concrete tools and toolschains that are predefined in varial are here.

The tool-baseclass and toolschains are defined in :ref:`toolinterface-module`.
More concrete tools that are defined in seperate modules are:

=================== ==========================
FSPlotter           :ref:`plotter-module`
RootFilePlotter     :ref:`plotter-module`
Webcreator          :ref:`webcreator-module`
CmsRunProxy         :ref:`cmsrunproxy-module`
FwliteProxy         :ref:`fwliteproxy-module`
=================== ==========================
"""

import glob
import os
import shutil

import analysis
import dbio
import diskio
import generators as gen
import settings
import wrappers

from toolinterface import \
    Tool, \
    ToolChain, \
    ToolChainIndie, \
    ToolChainVanilla
from cmsrunproxy import CmsRunProxy
from fwliteproxy import FwliteProxy
from plotter import FSPlotter, RootFilePlotter
from webcreator import WebCreator


class FSHistoLoader(Tool):
    """
    Loads histograms from fileservice.

    :param name:                str, tool name
    :param filter_keyfunc:      lambda, keyfunction with one argument
                                default: ``None`` (load all histograms)
    :param hook_loaded_histos:  generator to be applied after loading
                                default: ``None``
    :param io:                  io module
                                default: ``dbio``
    """
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
    """
    Copy contents of a directory. Preserves .htaccess files.

    :param dest:            str, destination path
    :param src:             str, source path,
                            default: ``''`` (copy everything in same directory)
    :param ignore:          list,
                            default:
                            ("*.root", "*.pdf", "*.eps", "*.log", "*.info")
    :param wipe_dest_dir:   bool, default: ``True``
    :param name:            str, tool name
    """
    def __init__(self, dest, src='',
                 ignore=("*.root", "*.pdf", "*.eps", "*.log", "*.info"),
                 wipe_dest_dir=True,
                 name=None):
        super(CopyTool, self).__init__(name)
        self.dest = dest
        self.src = src
        self.ignore = ignore
        self.wipe_dest_dir = wipe_dest_dir

    def run(self):
        src = os.path.abspath(self.src or os.path.join(self.cwd, '..'))
        dest = os.path.abspath(self.dest)

        # check for htaccess and copy it to src dirs
        htaccess = os.path.join(dest, '.htaccess')
        if os.path.exists(htaccess):
            for path, _, _ in os.walk(src):
                shutil.copy2(htaccess, path)

        # clean dest dir and copy
        if self.wipe_dest_dir:
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
    """
    Zip-compress a target folder.

    :param abs_path:    str, absolute path of tool to be zipped
    """
    def __init__(self, abs_path):
        super(ZipTool, self).__init__(None)
        self.abs_path = abs_path

    def run(self):
        p = os.path.join(settings.varial_working_dir, self.abs_path)
        os.system(
            'zip -r %s %s' % (p, p)
        )


class SampleNormalizer(Tool):
    """
    Normalize MC cross sections.

    With this tool all MC cross-section can be normalized to data, using one
    specific distribution. *Before* and *after* plots are stored as plots. The
    resulting factor is stored as result of this tool.

    :param filter_keyfunc:  lambda, keyfunction with one argument
    :param x_range_tuple:
    :param name:            str, tool name
    """
    can_reuse = False

    def __init__(self, filter_keyfunc, x_range_tuple, name=None):
        super(SampleNormalizer, self).__init__(name)
        self.filter_keyfunc = filter_keyfunc
        self.x_range = x_range_tuple

    def get_histos_n_factor(self):
        mcee, data = next(gen.fs_mc_stack_n_data_sum(
            self.filter_keyfunc
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


def mk_rootfile_plotter(name="RootFilePlots",
                        pattern='*.root',
                        flat=False,
                        plotter_factory=None):
    """
    Make a plotter chain that plots all content of all rootfiles in cwd.

    :param name:                str, name of the folder in which the output is
                                stored
    :param flat:                bool, flatten the rootfile structure
                                default: ``False``
    :param plotter_factory:     factory function for RootFilePlotter
                                default: ``None``
    """
    plotters = list(
        RootFilePlotter(f, plotter_factory, flat, name=f[:-5].split('/')[-1])
        for f in glob.iglob(pattern)
    )
    return ToolChain(name, [ToolChain(name, plotters)])






