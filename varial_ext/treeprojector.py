"""
Parallel tree projection using map/reduce.

Simple splitting by sample and file.
"""

from varial_ext.treeprojection_mr_impl import \
    jug_map_projection_per_file, \
    reduce_projection, \
    store_sample
import varial.multiproc
import varial.analysis
import varial.diskio
import varial.pklio
import varial.tools
import varial.util

import itertools
import glob
import time
import os


class TreeProjectorBase(varial.tools.Tool):
    """
    Project histograms from files with TTrees.

    :param filenames:               dict(sample -> list of files), e.g.   
                                    ``{'samplename': [file1, file2, ...], ...}``
    :param params:                  dict of params for ``map_projection``
    :param sec_sel_weight:          e.g. ``[('title', 'pt>5.', 'weight'), ...]``
    :param add_aliases_to_analysis: bool
    :param progress_callback:       optional function for usage with jug, which
                                    is called with 2 arguments (n_jobs, n_done)
                                    when new results are available
    :param name:                    tool name
    """
    io = varial.pklio

    def __init__(self,
                 filenames,
                 params,
                 sec_sel_weight=(('Histograms', '', ''),),
                 add_aliases_to_analysis=True,
                 progress_callback=None,
                 name=None,
                 ):
        super(TreeProjectorBase, self).__init__(name)
        self.filenames = filenames
        self.samples = filenames.keys()
        self.params = params
        self.sec_sel_weight = sec_sel_weight
        self.add_aliases_to_analysis = add_aliases_to_analysis

        assert filenames, 'dict(sample -> list of files), must not be empty'
        assert isinstance(filenames, dict), 'dict(sample -> list of files)'
        for sample, fnames in filenames.iteritems():
            assert fnames, 'no files for sample %s in %s' % (sample, self.name)

        # only for BatchTreeProjector
        self.progress_callback = progress_callback or (lambda a, b: None)
        self.jug_tasks = None
        self.iteration = -1

        self._init2()

    def _init2(self):
        pass

    def reuse(self):
        super(TreeProjectorBase, self).reuse()
        self._push_aliases_to_analysis()

    def _push_aliases_to_analysis(self):
        if self.add_aliases_to_analysis:
            varial.analysis.fs_aliases += self.result.wrps

    def prepare_params(self, selection, weight):
        params = dict(self.params)
        params['weight'] = weight
        params['selection'] = selection
        return params

    def prepare_mapiter(self, selection, weight, sample):
        params = self.prepare_params(selection, weight)
        files = self.filenames[sample]

        iterable = (
            (sample, f, params)
            for f in files
        )
        return iterable

    def finalize(self, sample_func):
        wrps = varial.diskio.generate_aliases(self.cwd + '*.root')
        wrps = varial.gen.gen_add_wrp_info(wrps, sample=sample_func)
        self.result = varial.wrappers.WrapperWrapper(list(wrps))
        os.system('touch %s/aliases.in.result' % self.cwd)
        self._push_aliases_to_analysis()


######################################### tree project directly on the node ###
def runtime_error_catcher(func):
    def catcher(args):
        try:
            res = func(args)
        except RuntimeError, e:
            res = 'RuntimeError', e.message
        return res
    return catcher


def gen_raise_runtime_error(iterator):
    for i in iterator:
        if isinstance(i, tuple) and i and i[0] == 'RuntimeError':
            raise RuntimeError(i[1])
        else:
            yield i


def _map_fwd(args):
    return varial.multiproc.exec_in_worker(
        runtime_error_catcher(jug_map_projection_per_file),
        args
    )


def _handle_sample(args):
    instance, sample = args
    instance = varial.analysis.lookup_tool(instance)
    return varial.multiproc.exec_in_worker(
        runtime_error_catcher(instance.handle_sample),
        sample
    )


class TreeProjector(TreeProjectorBase):
    def handle_sample(self, sample):
        self.message('INFO starting sample: ' + sample)

        n_procs = varial.settings.max_num_processes
        with varial.multiproc.NoDeamonWorkersPool(n_procs) as pool:
            for section, selection, weight in self.sec_sel_weight:
                if isinstance(weight, dict):
                    weight = weight[sample]
                res = self.prepare_mapiter(selection, weight, sample)
                res = pool.imap_unordered(_map_fwd, res)
                res = gen_raise_runtime_error(res)
                res = itertools.chain.from_iterable(res)
                res = reduce_projection(res, self.params)
                res = list(res)
                assert res, 'tree_projection did not yield any histograms'
                store_sample(sample, section, res)
                self.progress_callback(1, 1)

        varial.diskio.write_fileservice(sample)
        self.message('INFO sample done: ' + sample)

    def run(self):
        n_procs = min(varial.settings.max_num_processes, len(self.samples))
        with varial.multiproc.NoDeamonWorkersPool(n_procs) as pool:
            res = ((varial.analysis.get_current_tool_path(), s)
                   for s in self.samples)

            # work
            res = pool.imap_unordered(_handle_sample, res)
            res = gen_raise_runtime_error(res)
            for _ in res:
                pass

        # finalize
        self.finalize(lambda w: os.path.basename(w.file_path).split('.')[-2])


############################################### batch tree project with jug ###
try:
    import jug
except ImportError:
    jug = None

username = os.getlogin()
jug_work_dir_pat = '/nfs/dust/cms/user/{user}/varial_sge_exec'
jug_file_search_pat = jug_work_dir_pat + '/jug_file-*.py'
jug_file_path_pat = jug_work_dir_pat + '/jug_file-{i}-{section}-{sample}.py'

jugfile_content = """
sample = {sample}
section = {section}
params = {params}
files = {files}

inputs = list(
    (sample, f, params)
    for f in files
)

import varial_ext.treeprojection_mr_impl as mr
from jug.compound import CompoundTask
from jug import TaskGenerator
import jug.mapreduce
import cPickle
import os

@TaskGenerator
def finalize(result):
    os.remove(__file__)  # do not let other workers find the task anymore
    import varial
    mr.store_sample(sample, section, result)
    varial.diskio.write_fileservice(
        __file__.replace('.py', ''),
        initial_mode='UPDATE'
    )

result = CompoundTask(
    jug.mapreduce.mapreduce,
    mr.jug_reduce_projection,
    mr.jug_map_projection_per_file,
    inputs,
    map_step=4,
    reduce_step=8,
)
final_task = finalize(result)

jug.options.default_options.execute_wait_cycle_time_secs = 1
jug.options.default_options.execute_nr_wait_cycles = 1
"""


class BatchTreeProjector(TreeProjectorBase):
    def _init2(self):
        if not jug:
            raise ImportError('"Jug" is needed for BatchTreeProjector')

        exec_pat = jug_file_search_pat.format(user=username).replace('.py', '')
        if glob.glob(exec_pat):
            os.system('rm -rf ' + exec_pat)

    def launch_tasks(self, section, selection, weight):
        self.jug_tasks = []
        params = self.prepare_params(selection, weight)
        for sample in self.samples:
            if isinstance(weight, dict):
                params['weight'] = weight[sample]
            p_jugfile = jug_file_path_pat.format(
                i=self.iteration, user=username, section=section, sample=sample)
            p_jugres = os.path.splitext(p_jugfile)[0]

            # write jug_file
            with open(p_jugfile, 'w') as f:
                f.write(jugfile_content.format(
                    section=repr(section),
                    sample=repr(sample),
                    params=repr(params),
                    files=repr(self.filenames[sample]),
                ))

            # load new task
            self.jug_tasks.append((sample, p_jugres))

    def monitor_tasks(self):
        n_jobs = len(self.jug_tasks)
        n_done_prev, n_done = 0, -1
        items_done = [False] * n_jobs

        while n_done < n_jobs:

            errs = list(p + '.err.txt'
                for (_, p) in self.jug_tasks
                if os.path.exists(p + '.err.txt')
            )
            if errs:
                with open(errs[0]) as f:
                    raise RuntimeError(f.read())

            items_due = list(
                (not d) and os.path.exists(p + '.root')
                for (d, (_, p)) in itertools.izip(items_done, self.jug_tasks)
            )
            items_done = list(
                a or b
                for a, b in itertools.izip(items_done, items_due)
            )
            n_done_prev, n_done = n_done, sum(items_done)

            time.sleep(0.3)  # wait for write  # TODO wait for open exclusively
            if n_done_prev != n_done:
                for d, (_, p) in itertools.izip(items_due, self.jug_tasks):
                    if d:
                        os.system('mv %s.root %s' % (p, self.cwd))

                self.message('INFO {}/{} done'.format(n_done, n_jobs))
                self.progress_callback(n_jobs, n_done)

    def run(self):
        self.iteration += 1

        # clear last round of running (and the ones of 3 iterations ago)
        wd_junk = jug_file_search_pat.format(user=username)
        wd_junk = wd_junk.replace('*.py', '%d.*' % (self.iteration - 4))
        wd_junk_files = glob.glob(wd_junk)
        if wd_junk_files:
            os.system('rm ' + ' '.join(wd_junk_files))
        tooldir_junk_files = glob.glob('%s/*.root' % self.cwd)
        if tooldir_junk_files:
            os.system('rm ' + ' '.join(tooldir_junk_files))

        # do the work
        for section, selection, weight in self.sec_sel_weight:
            self.launch_tasks(section, selection, weight)
        self.monitor_tasks()

        # finalize
        self.finalize(
            lambda w: w.file_path.split('-')[-1][:-5]
        )


# TODO option for _not_ copying/moving result back (softlink?)
# TODO: move jug_constants somewhere sensible
