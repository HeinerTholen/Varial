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

from ast import literal_eval
import subprocess
import itertools
import random
import shutil
import glob
import os
import shutil
import time
import json

import analysis
import diskio
import generators as gen
import pklio
import settings
import wrappers

from toolinterface import \
    Tool, \
    ToolChain, \
    ToolChainIndie, \
    ToolChainVanilla, \
    ToolChainParallel
from plotter import \
    Plotter, \
    RootFilePlotter
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
            cp_func = lambda w, x, y: os.system('rsync -avz --delete {0} {1} {2}'.format(
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


class CompileTool(Tool):
    """
    Calls make in the directories given in paths.

    If compilation was needed (i.e. the output of make was different from
    "make: Nothing to be done for `all'") wanna_reuse will return False and
    by that cause all following modules to run.

    :param paths:   list of str: paths where make should be invoked
    """
    nothing_done = 'make: Nothing to be done for `all\'.\n'

    def __init__(self, paths):
        super(CompileTool, self).__init__()
        self.paths = paths

    def wanna_reuse(self, all_reused_before_me):
        nothing_compiled_yet = True
        for path in self.paths:
            self.message('INFO Compiling in: ' + path)
            # here comes a workaround: we need to examine the output of make,
            # but want to stream it directly to the console as well. Hence use
            # tee and look at the output after make finished.
            tmp_out = '/tmp/varial_compile_%06i' % random.randint(0, 999999)
            res = subprocess.call(
                # PIPESTATUS is needed to get the returncode from make
                ['make -j 9 | tee %s; test ${PIPESTATUS[0]} -eq 0' % tmp_out],
                cwd=path,
                shell=True,
            )
            if res:
                os.remove(tmp_out)
                raise RuntimeError('Compilation failed in: ' + path)
            if nothing_compiled_yet:
                with open(tmp_out) as f:
                    if not f.readline() == self.nothing_done:
                        nothing_compiled_yet = False
            os.remove(tmp_out)

        return nothing_compiled_yet and all_reused_before_me

    def run(self):
        pass


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
            Plotter.defaults_attrs['canvas_decorators']
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


class GitTagger(Tool):
    """
    A tool to automatically commit when running new tools (or amending a commit if tools are
    re-run) and keeping track of your tools and git history.

    In order to use this correctly, insert at the end of your main ToolChain that comprises 
    your analysis.
    """
    can_reuse = False

    def __init__(self, logfilename="GITTAGGER_LOG.txt"):
        super(GitTagger, self).__init__()
        self.logfilename = logfilename
        self.log_data = {}


    def print_tool_tree(self, toollist, res):
        if not len(res.children):
            toollist[res.name] = 0
        else:
            toollist[res.name] = {}
            for rname in sorted(res.children):
                self.print_tool_tree(toollist[res.name], res.children[rname])

    def compare_tool_tree(self, dict1, dict2):
        new_tool = 0
        for tool1 in dict1:
            if tool1 in dict2.keys():
                if isinstance(dict1[tool1], dict) and isinstance(dict2[tool1], dict):
                    new_tool = self.compare_tool_tree(dict1[tool1], dict2[tool1])
                    if new_tool == -1:
                        return new_tool
                elif (isinstance(dict1[tool1], dict) and not isinstance(dict2[tool1], dict))\
                    or (not isinstance(dict1[tool1], dict) and isinstance(dict2[tool1], dict)):
                    new_tool = -1
                    return new_tool
            else:
                new_tool_tmp = dict1[tool1]
                dict2[tool1] = new_tool_tmp
                new_tool = 1
        return new_tool

    def set_commit_hash(self, tool_dict, commit_hash=0, old_commit_hash=0):
        for tool in tool_dict:
            if isinstance(tool_dict[tool], dict):
                self.set_commit_hash(tool_dict[tool], commit_hash, old_commit_hash)
            else:
                if not old_commit_hash:
                    if tool_dict[tool] == 0:
                        tool_dict[tool] = commit_hash
                else:
                    if tool_dict[tool] == old_commit_hash:
                        tool_dict[tool] = commit_hash


    def new_commit(self, message=''):
        commit_msg = raw_input(message)
        if commit_msg == '':
            print "Not committed."
            return -1
        elif commit_msg == 'amend':
            previous_commit_msg = subprocess.check_output('git log -1 --pretty=%B', shell=True)
            previous_commit_hash = subprocess.check_output('git rev-parse --verify HEAD', shell=True)[:-2]
            os.system('git commit --amend -am "{0}"'.format(previous_commit_msg))
            new_commit_hash = subprocess.check_output('git rev-parse --verify HEAD', shell=True)[:-2]
            self.set_commit_hash(self.log_data, new_commit_hash, previous_commit_hash)
            return new_commit_hash
        else:
            os.system('git commit -am "From GitTagger: {0}"'.format(commit_msg))
            return subprocess.check_output('git rev-parse --verify HEAD', shell=True)[:-2]

    def update_logfile(self, logfilepath, log_data, commit_hash=-1):
        if isinstance(commit_hash, str):
            self.set_commit_hash(log_data, commit_hash)
        else:
            self.set_commit_hash(log_data, -1)
        with open(logfilepath, 'w') as logfile:
            json.dump(log_data, logfile, sort_keys=True, indent=4, separators=(',', ': '))



    def run(self):
        toollist = {}
        toollist[analysis.results_base.name] = {}
        for rname in sorted(analysis.results_base.children):
            self.print_tool_tree(toollist[analysis.results_base.name], analysis.results_base.children[rname])

        files_changed = False
        if os.path.isfile(analysis.cwd+self.logfilename):
            with open(analysis.cwd+self.logfilename, 'r') as logfile:
                self.log_data = json.load(logfile)
                new_tool = self.compare_tool_tree(toollist, self.log_data)
            if new_tool > 0:
                commit_hash = self.new_commit("New tool found, if you want to make new commit type a commit message; "\
                      "If you want to amend the latest commit, type 'amend'; "\
                      "If you don't want to commit, just press enter: ")
                self.update_logfile(analysis.cwd+self.logfilename, self.log_data, commit_hash)
            elif new_tool < 0:
                print "WARNING: two tools with same name but not of same class (i.e. Tool "\
                    "or ToolChain) found!"
                return
            else:
                commit_msg = raw_input("No new Tool found, want to amend commit? "\
                    "Press Enter if you don't want to amend; type 'y' or 'yes' to amend and keep the old commit message;"\
                    "to amend with a new message, type a new message: ")
                if commit_msg == '':
                    print "Not committed."
                elif any((commit_msg == i) for i in ['y', 'Y', 'yes', 'Yes', 'YES']):
                    previous_commit_msg = subprocess.check_output('git log -1 --pretty=%B', shell=True)
                    previous_commit_hash = subprocess.check_output('git rev-parse --verify HEAD', shell=True)[:-2]
                    os.system('git commit --amend -am "{0}"'.format(previous_commit_msg))
                    new_commit_hash = subprocess.check_output('git rev-parse --verify HEAD', shell=True)[:-2]
                    self.set_commit_hash(self.log_data, new_commit_hash, previous_commit_hash)
                else:
                    previous_commit_hash = subprocess.check_output('git rev-parse --verify HEAD', shell=True)[:-2]
                    os.system('git commit -a --amend -m "From GitTagger: {0}"'.format(commit_msg))
                    new_commit_hash = subprocess.check_output('git rev-parse --verify HEAD', shell=True)[:-2]
                    self.set_commit_hash(self.log_data, new_commit_hash, previous_commit_hash)
        else:
            self.log_data = toollist
            commit_msg = self.new_commit("No logfile found, if you want to make new commit type a commit message; "\
                      "If you want to amend the latest commit, type 'amend'; "\
                      "If you don't want to commit, just press enter: ")
            self.update_logfile(analysis.cwd+self.logfilename, self.log_data, commit_msg)


class TexContent(Tool):
    """
    Copies (and converts) content for usage in a tex document.

    For blocks of images, includestatements are printed into .tex files.
    These can be include in the main tex document.

    Image files in eps format are converted to pdf.

    IMPORTANT: absolute paths must be used in ``images`` and ``plain_files``!

    :param images:      ``{'blockname.tex': ['path/to/file1.eps', ...]}``
    :param plain_files: ``{'target_filename.tex': 'path/to/file1.tex', ...}``
    :param include_str: e.g. ``r'\includegraphics[width=0.49\textwidth]
                        {TexContent/%s}'`` where %s will be formatted with the
                        basename of the image
    :param dest_dir:    destination directory (default: tool path)
    """
    def __init__(self,
                 images,
                 plain_files,
                 include_str,
                 dest_dir=None,
                 name=None):
        super(TexContent, self).__init__(name)
        self.images = images
        self.tex_files = plain_files
        self.include_str = include_str
        self.dest_dir = dest_dir

    def _join(self, basename):
        return os.path.join(self.dest_dir, basename)

    @staticmethod
    def _hashified_filename(path):
        bname, ext = os.path.splitext(os.path.basename(path))
        hash_str = '_' + hex(hash(path))[-7:]
        return bname + hash_str

    def copy_image_files(self):
        for blockname, blockfiles in self.images.iteritems():
            hashified_and_path = list(
                (self._hashified_filename(bf), bf) for bf in blockfiles
            )

            # copy image files
            for hashified, path in hashified_and_path:
                p, ext = os.path.splitext(path)
                if ext == '.eps':
                    os.system('ps2pdf -dEPSCrop %s.eps %s.pdf' % (p, p))
                    ext = '.pdf'
                elif not ext in ('.pdf', '.png'):
                    raise RuntimeError(
                        'Only .eps, .pdf and .png images are supported.')
                shutil.copy(p+ext, self._join(hashified+ext))

            # make block file
            with open(self._join(blockname), 'w') as f:
                for hashified, _ in hashified_and_path:
                    f.write(self.include_str % hashified + '\n')

    def copy_plain_files(self):
        for fname, path, in self.tex_files.iteritems():
            shutil.copy(path, self._join(fname))

    def run(self):
        if not self.dest_dir:
            self.dest_dir = self.cwd
        self.copy_image_files()
        self.copy_plain_files()


def mk_rootfile_plotter(name="RootFilePlots",
                        pattern='*.root',
                        flat=False,
                        plotter_factory=None,
                        combine_files=False,
                        filter_keyfunc=None,
                        auto_legend=True,
                        legendnames=None,
                        **kws):
    """
    Make a plotter chain that plots all content of all rootfiles in cwd.

    Additional keywords are forwarded to the plotter instanciation.
    For running the plotter(s), use a Runner.

    :param name:                str, name of the folder in which the output is
                                stored
    :param pattern:             str, search pattern for rootfiles,
                                default: ``*.root``
    :param flat:                bool, flatten the rootfile structure
                                default: ``False``
    :param plotter_factory:     factory function for RootFilePlotter
                                default: ``None``
    :param combine_files:       bool, plot same histograms across rootfiles
                                into the same canvas. Does not work together
                                with ``flat`` option,
                                default: ``False``
    """
    def plotter_factory_kws(**kws_fctry):
        kws_fctry.update(kws)
        if plotter_factory:
            return plotter_factory(**kws_fctry)
        else:
            return Plotter(**kws_fctry)

    if kws:
        new_plotter_factory = plotter_factory_kws
    else:
        new_plotter_factory = plotter_factory

    if combine_files:
        tc = RootFilePlotter(
            pattern,
            new_plotter_factory,
            flat,
            name,
            filter_keyfunc,
            auto_legend,
            legendnames
        )
    else:
        plotters = list(
            RootFilePlotter(
                f,
                new_plotter_factory,
                flat,
                f[:-5].split('/')[-1],
                filter_keyfunc,
                auto_legend,
                legendnames
            )
            for f in glob.iglob(pattern)
        )
        tc = ToolChainParallel(name, plotters)
    return tc






