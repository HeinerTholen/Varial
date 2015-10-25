"""
Parallel tree projection using map/reduce.

Simple splitting by sample and file.
"""

from varial.extensions.treeprojection_mr_impl import \
    map_projection, \
    reduce_projection
import varial.multiproc
import varial.diskio
import varial.pklio
import varial.tools


def map_fwd(args):
    return varial.multiproc.exec_in_worker(lambda: next(map_projection(*args)))


class TreeProjector(varial.tools.Tool):
    """Project histograms from files with TTrees."""
    io = varial.pklio

    def __init__(self,
                 name,
                 sample_filename_dict,
                 params,
                 add_aliases_to_analysis=True
                 ):
        super(TreeProjector, self).__init__(name)
        self.s_f_dict = sample_filename_dict
        self.params = params
        self.add_aliases_to_analysis = add_aliases_to_analysis

    def _push_aliases_to_analysis(self):
        if self.add_aliases_to_analysis:
            varial.analysis.fs_aliases += self.result.wrps

    def store_sample(self, sample, result):
        fs_wrp = varial.analysis.fileservice(sample, False)
        fs_wrp.sample = sample
        for sample_name, histo in result:
            _, name = sample_name.split()
            setattr(fs_wrp, name, histo)
        varial.diskio.write(fs_wrp)

    def handle_sample(self, sample, filenames):
        self.message('INFO starting sample: ' + sample)

        pool = varial.multiproc.NoDeamonWorkersPool(
            varial.settings.max_num_processes)

        iterable = (
            ('%s %s %s'%(sample, h, f), self.params)
            for f in filenames
            for h in self.params['histos']
        )

        res = list(reduce_projection(
            pool.imap_unordered(map_fwd, iterable), self.params))

        pool.close()
        pool.join()
        self.message('INFO sample done: ' + sample)
        return res

    def reuse(self):
        super(TreeProjector, self).reuse()
        self._push_aliases_to_analysis()

    def run(self):
        for s, fs in self.s_f_dict.iteritems():
            self.store_sample(s, self.handle_sample(s, fs))

        self.result = varial.wrappers.WrapperWrapper(
            list(varial.diskio.generate_aliases(self.cwd + '*.root'))
        )
        self._push_aliases_to_analysis()
