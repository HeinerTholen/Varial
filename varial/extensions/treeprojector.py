"""
Parallel tree projection using map/reduce.

Simple splitting by sample and file.
"""

from varial.extensions.treeprojection_mr_impl import \
    jug_map_projection_per_file, \
    reduce_projection
import varial.multiproc
import varial.analysis
import varial.diskio
import varial.pklio
import varial.tools
import varial.util

import subprocess
import itertools
import glob
import time
import os


class TreeProjectorBase(varial.tools.Tool):
    """
    Project histograms from files with TTrees.

    :param samples:                 list of sample names
    :param file_pattern:            e.g. ``'path/to/myfile_*.root'``
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
                 samples,
                 file_pattern,
                 params,
                 sec_sel_weight=(('Histograms', '', ''),),
                 add_aliases_to_analysis=True,
                 progress_callback=None,
                 name=None,
                 ):
        super(TreeProjectorBase, self).__init__(name)
        self.samples = samples
        self.file_pattern = file_pattern
        self.params = params
        self.sec_sel_weight = sec_sel_weight
        self.add_aliases_to_analysis = add_aliases_to_analysis
        self.filenames = None

        # only for JugTreeProjector
        self.progress_callback = progress_callback or (lambda a, b: None)
        self.sge_job_numbers = []
        self.jug_tasks = None

        self.initialize()

    def initialize(self):
        pass

    def reuse(self):
        super(TreeProjectorBase, self).reuse()
        self._push_aliases_to_analysis()

    def _push_aliases_to_analysis(self):
        if self.add_aliases_to_analysis:
            varial.analysis.fs_aliases += self.result.wrps

    @staticmethod
    def store_sample(sample, section, result):
        fs_wrp = varial.analysis.fileservice(section)
        fs_wrp.sample = sample
        for sample_histoname, histo in result:
            _, name = sample_histoname.split()
            setattr(fs_wrp, name, histo)

    def prepare_mapiter(self, weight, selection, sample):
        params = dict(self.params)
        params['weight'] = weight
        params['selection'] = selection

        iterable = (
            (sample, f, params)
            for f in self.filenames
            if sample in f
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
            iterable = self.prepare_mapiter(weight, selection, sample)

            res = list(reduce_projection(itertools.chain.from_iterable(
                pool.imap_unordered(_map_fwd, iterable)
            ), self.params))
            self.store_sample(sample, section, res)

        pool.close()
        pool.join()
        varial.diskio.write_fileservice(sample)
        self.message('INFO sample done: ' + sample)

    def run(self):
        self.filenames = glob.glob(self.file_pattern)

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
num_sge_jobs = 40
jug_work_dir_pat = '/nfs/dust/cms/user/*/varial_sge_exec'
jug_file_path_pat = jug_work_dir_pat + '/jug_file.py'
jug_work_dir = jug_work_dir_pat.replace('*', os.getlogin())
jug_file_path = jug_file_path_pat.replace('*', os.getlogin())
jug_data_path = jug_work_dir + '/jug_file.jugdata'
jug_log_dir = jug_work_dir.replace('varial_sge_exec', 'varial_sge_log')

sge_job_conf = """#!/bin/bash
#$ -l os=sld6
#$ -l site=hh
#$ -cwd
#$ -V
#$ -l h_rt=02:00:00
#$ -l h_vmem=2G
#$ -l h_fsize=2G
cd /tmp/
python -c "\
from varial.extensions.sgeworker import SGEWorker; \
SGEWorker(${SGE_TASK_ID}, {jug_file_path}, {jug_file_path_pat}).start(); \
"
"""

jugfile_content = """
inputs = {inputs}

from varial.extensions.treeprojection_mr_impl import \
    jug_map_projection_per_file, \
    jug_reduce_projection
from jug.compound import CompoundTask
import jug.mapreduce

tasks = list(
    CompoundTask(
        jug.mapreduce.mapreduce,
        jug_reduce_projection,
        jug_map_projection_per_file,
        inp,
        map_step=1
    ) for inp in inputs
)
"""


class SGETreeProjector(TreeProjectorBase):
    def initialize(self):
        # prepare dirs
        if os.path.exists(jug_work_dir):
            raise RuntimeError(
                'Workdir exists already: %s. Please clear it.' % jug_work_dir
            )
        if not os.path.exists(jug_log_dir):
            os.mkdir(jug_log_dir)

        os.mkdir(jug_work_dir)
        os.system('chmod g+w %s' % jug_work_dir)
        os.system('umask g+w %s' % jug_work_dir)  # let's collaborate! =)

        # prepare sge config with paths
        job_sh = os.path.join(jug_work_dir, 'jug_worker.sh')
        with open(job_sh, 'w') as f:
            f.write(sge_job_conf.format(
                jug_file_path=jug_file_path,
                jug_file_path_pat=jug_file_path_pat
            ))

        # launch sge jobs
        qsub_cmd = [
            'qsub',
            '-t 1-%d' % num_sge_jobs,
            '-o %s/' % jug_log_dir,
            '-e %s/' % jug_log_dir,
            job_sh,
        ]
        proc = subprocess.Popen(qsub_cmd, shell=True, stdout=subprocess.PIPE)
        job_num = (proc.communicate()[0].split()[2]).split('.')[0]
        self.sge_job_numbers.append(job_num)

    def __del__(self):
        # kill jobs and remove jug_data_dir
        os.system('qdel ' + ','.join(self.sge_job_numbers))
        os.system('rm -r %s' % jug_work_dir)

    def create_jugfile(self, selection, weight):
        inputs = list(
            list(self.prepare_mapiter(weight, selection, sample))
            for sample in self.samples
        )

        with open(jug_file_path, 'w') as f:
            f.write(jugfile_content.format(inputs=repr(inputs)))

    def load_tasks(self):
        import jug, imp
        jug.init(jug_file_path, jug_data_path)
        jug_file = imp.load_source('jug_file', jug_file_path)

        self.jug_tasks = list(jug_file.tasks)
        for t in self.jug_tasks:
            t.loading_done = False

    def monitor_progress(self, section):
        n_jobs = len(self.jug_tasks)
        n_done_pre, n_done = 0, -1
        while n_done < n_jobs:
            time.sleep(0.2)
            n_done_pre, n_done = n_done, sum(t.can_load for t in self.jug_tasks)
            if n_done_pre != n_done:
                self.collect_result(section)
                self.progress_callback(n_jobs, n_done)

    def collect_result(self, section):
        for t in self.jug_tasks:
            if t.can_load and not t.loading_done:
                sample = t.result[0][0].split()[0]
                self.store_sample(sample, section, t.result)
                varial.diskio.write_fileservice(sample, initial_mode='UPDATE')
                t.loading_done = True

    @staticmethod
    def remove_jugfile():
        os.system('rm ' + jug_file_path)
        os.system('rm -r ' + jug_data_path)

    def run(self):
        os.system('rm %s/*.root' % self.cwd)  # clear last round of running

        for section, selection, weight in self.sec_sel_weight:
            self.create_jugfile(selection, weight)
            self.load_tasks()
            self.monitor_progress(section)
            self.remove_jugfile()

        self.result = varial.wrappers.WrapperWrapper(
            list(varial.diskio.generate_aliases(self.cwd + '*.root'))
        )
        self._push_aliases_to_analysis()


# TODO launch new jobs when old ones die
