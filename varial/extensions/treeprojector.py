"""
Parallel tree projection using map/reduce.

Simple splitting by sample and file.
"""

from varial.extensions.treeprojection_mr_impl import \
    jug_map_projection_per_file, \
    reduce_projection
import varial.multiproc
import varial.diskio
import varial.pklio
import varial.tools
import varial.util

import itertools
import glob


def _map_fwd(args):
    return varial.multiproc.exec_in_worker(jug_map_projection_per_file, args)


def _handle_sample(args):
    instance, sample = args
    varial.multiproc.exec_in_worker(lambda: instance.handle_sample(sample))


class TreeProjector(varial.tools.Tool):
    """
    Project histograms from files with TTrees.

    :param samples:                 list of sample names
    :param file_pattern:            e.g. ``'path/to/myfile_*.root'``
    :param params:                  dict of params for ``map_projection``
    :param sec_sel_weight:          e.g. ``[('title', 'pt>5.', 'weight'), ...]``
    :param add_aliases_to_analysis: bool
    :param name:                    tool name
    """
    io = varial.pklio

    def __init__(self,
                 samples,
                 file_pattern,
                 params,
                 sec_sel_weight=(('Histograms', '', ''),),
                 add_aliases_to_analysis=True,
                 name=None,
                 ):
        super(TreeProjector, self).__init__(name)
        self.samples = samples
        self.file_pattern = file_pattern
        self.params = params
        self.sec_sel_weight = sec_sel_weight
        self.add_aliases_to_analysis = add_aliases_to_analysis
        self.filenames = None

    def _push_aliases_to_analysis(self):
        if self.add_aliases_to_analysis:
            varial.analysis.fs_aliases += self.result.wrps

    @staticmethod
    def store_sample(sample, section, result):
        fs_wrp = varial.analysis.fileservice(section)
        fs_wrp.sample = sample
        for sample_name, histo in result:
            _, name = sample_name.split()
            setattr(fs_wrp, name, histo)

    def handle_sample(self, sample):
        self.message('INFO starting sample: ' + sample)
        pool = varial.multiproc.NoDeamonWorkersPool(
            varial.settings.max_num_processes)

        for section, selection, weight in self.sec_sel_weight:

            params = dict(self.params)
            params['weight'] = weight
            params['selection'] = selection

            iterable = (
                (sample, f, params)
                for f in self.filenames
                if sample in f
            )

            res = list(reduce_projection(itertools.chain.from_iterable(
                pool.imap_unordered(_map_fwd, iterable)
            ), params))
            self.store_sample(sample, section, res)

        pool.close()
        pool.join()
        varial.diskio.write_fileservice(sample)
        self.message('INFO sample done: ' + sample)

    def reuse(self):
        super(TreeProjector, self).reuse()
        self._push_aliases_to_analysis()

    def run(self):
        self.filenames = glob.glob(self.file_pattern)

        pool = varial.multiproc.NoDeamonWorkersPool(
            min(varial.settings.max_num_processes, len(self.samples)))
        iterable = ((self, s) for s in self.samples)

        for _ in pool.imap_unordered(_handle_sample, iterable):
            pass

        pool.close()
        pool.join()

        self.result = varial.wrappers.WrapperWrapper(
            list(varial.diskio.generate_aliases(self.cwd + '*.root'))
        )
        self._push_aliases_to_analysis()
