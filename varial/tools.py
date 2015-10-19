"""
All concrete tools and toolschains that are predefined in varial are here.

The tool-baseclass and toolschains are defined in :ref:`toolinterface-module`.
More concrete tools that are defined in seperate modules are:

=================== ==========================
Plotter             :ref:`plotter-module`
RootFilePlotter     :ref:`plotter-module`
Webcreator          :ref:`webcreator-module`
=================== ==========================
"""

from ast import literal_eval
import itertools
import shutil
import glob
import os

import generators as gen
import analysis
import wrappers
import diskio
import pklio

from toolinterface import \
    Tool, \
    ToolChain, \
    ToolChainIndie, \
    ToolChainVanilla, \
    ToolChainParallel
from plotter import \
    Plotter, \
    RootFilePlotter, \
    mk_rootfile_plotter
from webcreator import \
    WebCreator


class Runner(ToolChain):
    """Runs tools upon instanciation (including proper folder creation)."""
    def __init__(self, tool, default_reuse=False):
        super(Runner, self).__init__(None, [tool], default_reuse)
        analysis.reset()
        self.run()


class PrintToolTree(Tool):
    """Calls analysis.print_tool_tree()"""
    can_reuse = False

    def run(self):
        analysis.print_tool_tree()


class UserInteraction(Tool):
    def __init__(self,
                 prompt='Hit enter to continue. Kill me otherwise.',
                 eval_result=False,
                 can_reuse=True,
                 name=None):
        super(UserInteraction, self).__init__(name)
        self.prompt = prompt
        self.eval_result = eval_result
        self.can_reuse = can_reuse

    def run(self):
        if self.eval_result:
            self.message('INFO Input will be evaluated as python code.')
        if self.can_reuse:
            self.message('INFO Input might be reused.')
        res = raw_input(self.prompt+' ')
        if self.eval_result:
            res = literal_eval(res)
        self.result = wrappers.Wrapper(input=res)


class HistoLoader(Tool):
    """
    Loads histograms from any rootfile or from fileservice.

    :param name:                str, tool name
    :param pattern:             str, pattern for filesearch, e.g. ``*.root``,
                                default: None (load from fileservice)
    :param filter_keyfunc:      lambda, keyfunction with one argument,
                                default: ``None`` (load all histograms)
    :param hook_loaded_histos:  generator to be applied after loading,
                                default: ``None``
    :param io:                  io module,
                                default: ``dbio``
    """
    def __init__(self,
                 pattern=None,
                 filter_keyfunc=None,
                 hook_loaded_histos=None,
                 raise_on_empty_result=True,
                 io=pklio,
                 name=None):
        super(HistoLoader, self).__init__(name)
        self.pattern = pattern
        self.filter_keyfunc = filter_keyfunc
        self.hook_loaded_histos = hook_loaded_histos
        self.raise_on_empty_result = raise_on_empty_result
        self.io = io

    def run(self):
        if self.pattern:
            wrps = gen.dir_content(self.pattern)
            wrps = itertools.ifilter(self.filter_keyfunc, wrps)
            wrps = gen.load(wrps)
            if self.hook_loaded_histos:
                wrps = self.hook_loaded_histos(wrps)
            wrps = gen.sort(wrps)
        else:
            wrps = gen.fs_filter_active_sort_load(self.filter_keyfunc)
            if self.hook_loaded_histos:
                wrps = self.hook_loaded_histos(wrps)
        self.result = list(wrps)

        if not self.result:
            if self.raise_on_empty_result:
                raise RuntimeError('ERROR No histograms found.')
            else:
                self.message('ERROR No histograms found.')


class CopyTool(Tool):
    """
    Copy contents of a directory. Preserves .htaccess files.

    :param dest:            str, destination path
    :param src:             str, source path,
                            default: ``''`` (copy everything in same directory)
    :param ignore:          list,
                            default:
                            ``("*.root", "*.pdf", "*.eps", "*.log", "*.info")``
    :param wipe_dest_dir:   bool, default: ``True``
    :param name:            str, tool name
    """
    def __init__(self, dest, src='',
                 ignore=("*.root", "*.pdf", "*.eps", "*.log", "*.info"),
                 wipe_dest_dir=True,
                 name=None,
                 use_rsync=False):
        super(CopyTool, self).__init__(name)
        self.dest = dest.replace('~', os.getenv('HOME'))
        self.src = src.replace('~', os.getenv('HOME'))
        self.ignore = ignore
        self.wipe_dest_dir = wipe_dest_dir
        self.use_rsync = use_rsync

    def def_copy(self, src_objs, dest, ignore):
        ign_pat = shutil.ignore_patterns(*ignore)
        for src in src_objs:
            self.message('INFO Copying: ' + src)
            if os.path.isdir(src):
                f = os.path.basename(src)
                shutil.copytree(
                    src,
                    os.path.join(dest, f),
                    ignore=ign_pat,
                )
            else:
                shutil.copy2(src, dest)

    def run(self):
        if self.use_rsync:
            self.wipe_dest_dir = False
            self.ignore = list('--exclude='+w for w in self.ignore)
            cp_func = lambda w, x, y: os.system(
                'rsync -avz --delete {0} {1} {2}'.format(
                    ' '.join(w), x, ' '.join(y)))
        else:
            cp_func = lambda w, x, y: self.def_copy(w, x, y)

        if self.src:
            src = os.path.abspath(self.src)
            src_objs = glob.glob(src)
        elif self.cwd:
            src = os.path.abspath(os.path.join(self.cwd, '..'))
            src_objs = glob.glob(src + '/*')
        else:
            src = os.getcwd()
            src_objs = glob.glob(src + '/*')
        dest = os.path.abspath(self.dest)

        # check for htaccess and copy it to src dirs
        htaccess = os.path.join(dest, '.htaccess')
        if os.path.exists(htaccess):
            for src in src_objs:
                for path, _, _ in os.walk(src):
                    shutil.copy2(htaccess, path)

        # clean dest dir
        if self.wipe_dest_dir:
            src_basenames = list(os.path.basename(p) for p in src_objs)
            for f in glob.glob(dest + '/*'):
                if os.path.isdir(f) and os.path.basename(f) in src_basenames:
                    self.message('INFO Deleting: ' + f)
                    shutil.rmtree(f, True)

        # copy
        cp_func(src_objs, dest, self.ignore)


class Hadd(Tool):
    """
    Apply hadd for a folder of histograms.

    All *.root files in the ``src_path`` directory that do not apply to one of
    the basenames are soft-linked into the new output directory.

    :param src_path:            str, *relative* path to input dir
    :param basenames:           list of str, basenames for files to be merged
                                (e.g. 'QCD' for 'QCD_XtoY', 'QCD_YtoZ'...)
    :param remake_aliases:      bool, if true, anaylsis.fs_aliases are replaced
                                with all output of this tool.
    :param name:                str, tool name
    """
    io = pklio

    def __init__(self,
                 src_glob_path,
                 basenames,
                 remake_aliases=True,
                 samplename_func=lambda w: os.path.basename(w.file_path),
                 name=None):
        super(Hadd, self).__init__(name)
        self.src_glob_path = src_glob_path
        self.src_path = os.path.dirname(src_glob_path)
        self.basenames = basenames
        self.remake_aliases = remake_aliases
        self.samplename_func = samplename_func
        assert(type(basenames) in (list, tuple))

    def produce_aliases(self):
        wrps = list(diskio.generate_aliases(os.path.join(self.cwd, '*.root')))
        for w in wrps:
            w.sample = self.samplename_func(w)
        self.result = wrappers.WrapperWrapper(wrps)

    def reuse(self):
        super(Hadd, self).reuse()
        if self.remake_aliases:
            analysis.fs_aliases = self.result.wrps

    def run(self):
        super(Hadd, self).run()
        join = os.path.join

        # sort input files
        input_files = glob.glob(join(self.cwd, self.src_glob_path))
        basename_map = dict((b, []) for b in self.basenames)
        other_inputs = []
        for inp_file in input_files:
            inp_file = os.path.basename(inp_file)
            file_path = join(self.cwd, self.src_path, inp_file)
            if any(inp_file.startswith(b) for b in self.basenames):
                for b in self.basenames:
                    if inp_file.startswith(b):
                        basename_map[b].append(file_path)
            else:
                other_inputs.append(file_path)

        # apply hadd
        for basename, files in basename_map.iteritems():
            if not files:
                self.message('WARNING No files for basename: %s' % basename)
                continue

            cmd = 'hadd -f -v 1 %s.root ' % join(self.cwd, basename)
            os.system(cmd + ' '.join(files))

        # link others
        for f in other_inputs:
            os.system('ln -sf %s %s' % (os.path.relpath(f, self.cwd), self.cwd))

        # aliases
        self.produce_aliases()
        if self.remake_aliases:
            analysis.fs_aliases = self.result.wrps

