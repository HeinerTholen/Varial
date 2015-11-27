"""
Parallel tree projection using map/reduce.

Simple splitting by sample and file.
"""

from varial.extensions.treeprojection_mr_impl import \
    jug_map_projection_per_file, \
    reduce_projection, \
    store_sample
import varial.multiproc
import varial.analysis
import varial.diskio
import varial.pklio
import varial.tools
import varial.util

import subprocess
import itertools
import cPickle
import glob
import time
import os


class TreeProjectorBase(varial.tools.Tool):
    """
    Project histograms from files with TTrees.

    :param samples:                 list of sample names
    :param filenames:               dict(sample -> list of files), e.g.   
                                    ``{'samplename': [file1, file2, ...], ...}``
    :param params:                  dict of params for ``map_projection``
    :param sec_sel_weight:          e.g. ``[('title', 'pt>5.', 'weight'), ...]``
    :param add_aliases_to_analysis: bool
    :param progress_callback:       optional function for usage with jug, which
                                    is called with 2 arguments (n_jobs, n_done)
                                    when new results are available
    :param suppress_job_submission: bool, for debugging
    :param name:                    tool name
    """
    io = varial.pklio

    def __init__(self,
                 samples,
                 filenames,
                 params,
                 sec_sel_weight=(('Histograms', '', ''),),
                 add_aliases_to_analysis=True,
                 progress_callback=None,
                 suppress_job_submission=False,
                 name=None,
                 ):
        super(TreeProjectorBase, self).__init__(name)
        self.samples = samples
        self.params = params
        self.sec_sel_weight = sec_sel_weight
        self.add_aliases_to_analysis = add_aliases_to_analysis
        self.filenames = filenames

        # only for JugTreeProjector
        self.progress_callback = progress_callback or (lambda a, b: None)
        self.suppress_job_submission = suppress_job_submission
        self.jug_tasks = None
        self.iteration = -1

        self.initialize()

    def initialize(self):
        pass

    def reuse(self):
        super(TreeProjectorBase, self).reuse()
        self._push_aliases_to_analysis()

    def _push_aliases_to_analysis(self):
        os.system('touch %s/aliases.in.result' % self.cwd)
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


######################################### tree project directly on the node ###
def _map_fwd(args):
    return varial.multiproc.exec_in_worker(jug_map_projection_per_file, args)


def _handle_sample(args):
    instance, sample = args
    instance = varial.analysis.lookup_tool(instance)
    varial.multiproc.exec_in_worker(lambda: instance.handle_sample(sample))


class TreeProjector(TreeProjectorBase):
    def handle_sample(self, sample):
        self.message('INFO starting sample: ' + sample)
        pool = varial.multiproc.NoDeamonWorkersPool(
            varial.settings.max_num_processes)

        for section, selection, weight in self.sec_sel_weight:
            iterable = self.prepare_mapiter(selection, weight, sample)

            res = list(reduce_projection(itertools.chain.from_iterable(
                pool.imap_unordered(_map_fwd, iterable)
            ), self.params))
            store_sample(sample, section, res)

        pool.close()
        pool.join()
        varial.diskio.write_fileservice(sample)
        self.message('INFO sample done: ' + sample)

    def run(self):
        pool = varial.multiproc.NoDeamonWorkersPool(
            min(varial.settings.max_num_processes, len(self.samples)))
        iterable = ((varial.analysis.get_current_tool_path(), s)
                    for s in self.samples)

        for _ in pool.imap_unordered(_handle_sample, iterable):
            pass

        pool.close()
        pool.join()

        self.result = varial.wrappers.WrapperWrapper(
            list(varial.diskio.generate_aliases(self.cwd + '*.root'))
        )
        self._push_aliases_to_analysis()


############################################## tree project on sge with jug ###
try:
    import jug, imp
except ImportError:
    jug, imp = None, None

num_sge_jobs = 30
username = os.getlogin()
jug_work_dir_pat = '/nfs/dust/cms/user/{user}/varial_sge_exec'
jug_file_search_pat = jug_work_dir_pat + '/jug_file_*.py'
jug_file_path_pat = jug_work_dir_pat + '/jug_file_.{i}.{section}.{sample}.py'

jug_work_dir = jug_work_dir_pat.format(user=username)
jug_log_dir = jug_work_dir.replace('varial_sge_exec', 'varial_sge_log')

sge_job_conf = """#!/bin/bash
#$ -l os=sld6
#$ -l site=hh
#$ -cwd
#$ -V
#$ -l h_rt=01:00:00
#$ -l h_vmem=2G
#$ -l h_fsize=2G#
#$ -o {jug_log_dir}/
#$ -e {jug_log_dir}/
#$ -t 1-{num_sge_jobs}
cd /tmp/
python -c "\
from varial.extensions.sgeworker import SGEWorker; \
SGEWorker(${SGE_TASK_ID}, '{user}', '{jug_file_path_pat}').start(); \
"
"""

jugfile_content = """
sample = {sample}
section = {section}
params = {params}
files = {files}

inputs = list(
    (sample, f, params)
    for f in files
)

import varial.extensions.treeprojection_mr_impl as mr
from jug.compound import CompoundTask
from jug import TaskGenerator
import jug.mapreduce
import cPickle
import os

@TaskGenerator
def finalize(result):
    os.remove(__file__)
    import varial
    mr.store_sample(sample, section, result)
    varial.diskio.write_fileservice(
        __file__.replace('.py', ''), initial_mode='UPDATE')

result = CompoundTask(
    jug.mapreduce.mapreduce,
    mr.jug_reduce_projection,
    mr.jug_map_projection_per_file,
    inputs,
    map_step=4,
    reduce_step=8,
)
copy_res = finalize(result)

jug.options.default_options.execute_wait_cycle_time_secs = 1
jug.options.default_options.execute_nr_wait_cycles = 1
"""


class SGETreeProjector(TreeProjectorBase):
    def initialize(self):
        if not jug:
            raise ImportError('"Jug" is needed for SGETreeProjector')

        # prepare dirs
        if not os.path.exists(jug_log_dir):
            os.mkdir(jug_log_dir)

        if not os.path.exists(jug_work_dir):
            os.mkdir(jug_work_dir)
            os.system('chmod g+w %s' % jug_work_dir)
            os.system('umask g+w %s' % jug_work_dir)  # let's collaborate! =)

        # clear some dirs
        exec_pat = jug_file_search_pat.format(user=username).replace('.py', '')
        log_pat = jug_log_dir + '/jug_worker.sh.*'
        if glob.glob(exec_pat):
            os.system('rm -rf ' + exec_pat)
        if glob.glob(log_pat):
            os.system('rm -rf ' + log_pat)

        self.launch_workers()

    def launch_workers(self):
        if self.suppress_job_submission:
            return

        # how many are needed?
        def parse_num_jobs(qstat_line):
            if not qstat_line.strip():  # empty line
                return 0
            token = qstat_line.split()[-1]  # get last column
            if ':' in token:  #
                running, tot = token.split(':')[0].split('-')
                return int(tot) - int(running)
            else:
                return 1

        qstat_cmd = ['qstat | grep jug_worker']
        proc = subprocess.Popen(qstat_cmd, shell=True, stdout=subprocess.PIPE)
        res = proc.communicate()[0]
        res = (parse_num_jobs(line) for line in res.split('\n'))
        n_workers = sum(res)
        n_workers_needed = num_sge_jobs - n_workers

        # only submit if at least 5 workers are needed
        if n_workers_needed < 5:
            return

        # prepare sge config with paths
        job_sh = os.path.join(jug_work_dir, 'jug_worker.sh')
        with open(job_sh, 'w') as f:
            f.write(sge_job_conf.format(
                SGE_TASK_ID='{SGE_TASK_ID}',  # should stay
                jug_log_dir=jug_log_dir,
                num_sge_jobs=n_workers_needed,
                user=username,
                jug_file_path_pat=jug_file_search_pat,
            ))

        qsub_cmd = ['qsub ' + job_sh]
        proc = subprocess.Popen(qsub_cmd, shell=True, stdout=subprocess.PIPE)
        res = proc.communicate()[0]
        if not res.strip():
            raise RuntimeError('Job submission failed.')

    def launch_tasks(self, section, selection, weight):
        self.jug_tasks = []
        params = self.prepare_params(selection, weight)
        for sample in self.samples:
            p_jugfile = jug_file_path_pat.format(
                i=self.iteration, user=username, section=section, sample=sample)
            p_jugres = p_jugfile.replace('.py', '.root')

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

    def monitor_tasks(self, section):
        n_jobs = len(self.jug_tasks)
        n_done_prev, n_done = 0, -1
        items_done = [False] * n_jobs

        while n_done < n_jobs:
            items_due = map(
                lambda (d, (_, p)): (not d) and os.path.exists(p),
                itertools.izip(items_done, self.jug_tasks)
            )
            items_done = list(
                a or b
                for a, b in itertools.izip(items_done, items_due)
            )
            n_done_prev, n_done = n_done, sum(items_done)

            time.sleep(0.3)  # wait for file write    # TODO check file lock?
            if n_done_prev != n_done:
                for d, (s, p) in itertools.izip(items_due, self.jug_tasks):
                    if d:
                        os.system('cp %s %s' % (p, self.cwd))

                self.message(
                    'INFO %d/%d done for section "%s"'
                    % (n_done, n_jobs, section)
                )
                self.progress_callback(n_jobs, n_done)

    def run(self):
        self.iteration += 1

        # clear last round of running (and the ones of 3 iterations ago)
        glob_pat = jug_file_search_pat.format(user=username)
        glob_pat = glob_pat.replace('*.py', '%d.*' % (self.iteration - 4))
        for f in glob.glob(glob_pat):
            os.system('rm %s' % f)
        for f in glob.glob('%s/*.root' % self.cwd):
            os.system('rm %s' % f)

        for section, selection, weight in self.sec_sel_weight:
            self.launch_workers()
            self.launch_tasks(section, selection, weight)
            self.monitor_tasks(section)

        if self.add_aliases_to_analysis:
            wrps = varial.diskio.generate_aliases(self.cwd + '*.root')
            wrps = varial.gen.gen_add_wrp_info(
                wrps, sample=lambda w: w.file_path.split('.')[-2])
            self.result = varial.wrappers.WrapperWrapper(list(wrps))
            self._push_aliases_to_analysis()


# TODO #1: for all that provide aliases: add sample
# TODO #2: make diskio look for aliases info file
