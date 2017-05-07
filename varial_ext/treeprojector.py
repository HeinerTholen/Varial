"""
Parallel tree projection using map/reduce.
"""

import varial_ext.treeprojection_mr_impl as mr
import varial.multiproc
import varial.analysis
import varial.diskio
import varial.pklio
import varial.tools
import varial.util
import itertools
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
                 hot_result=False,
                 add_aliases_to_analysis=True,
                 name=None,
                 ):
        super(TreeProjectorBase, self).__init__(name)
        self.filenames = filenames
        self.params = params
        self.sec_sel_weight = sec_sel_weight
        self.add_aliases_to_analysis = add_aliases_to_analysis
        self.use_hot_result = hot_result
        self.hot_result = []
        if hot_result:
            self.no_reset = True


        assert filenames, 'dict(sample -> list of files), must not be empty'
        assert isinstance(filenames, dict), 'dict(sample -> list of files)'
        for sample, fnames in filenames.items():
            if not fnames:
                self.message('WARNING no files for sample %s in %s'
                             % (sample, self.name))
                del filenames[sample]

        self.samples = filenames.keys()

    def reuse(self, _=False):
        super(TreeProjectorBase, self).reuse(self.add_aliases_to_analysis)
        self._push_aliases_to_analysis()

    def _push_aliases_to_analysis(self):
        if self.add_aliases_to_analysis:
            varial.analysis.fs_aliases += self.result.wrps

    def prepare_params(self, selection, weight, sample):
        params = dict(self.params)
        params['weight'] = weight[sample] if isinstance(weight, dict) else weight
        params['selection'] = selection
        return params

    def prepare_mapiter(self, selection, weight, sample):
        params = self.prepare_params(selection, weight, sample)
        files = self.filenames[sample]

        iterable = (
            (sample, f, params)
            for f in files
        )
        return iterable

    def put_aliases(self, sample_func, wrps=None):
        if not wrps:
            wrps = varial.diskio.generate_aliases(self.cwd + '*.root')
            wrps = varial.gen.gen_add_wrp_info(wrps, sample=sample_func)
        self.result = varial.wrappers.WrapperWrapper(list(wrps))
        os.system('touch %s/aliases.in.result' % self.cwd)
        self._push_aliases_to_analysis()


######################################### tree project directly on the node ###
def _handle_sample(args):
    instance, sample = args
    instance = varial.analysis.lookup_tool(instance)
    return instance.handle_sample(sample),


class TreeProjector(TreeProjectorBase):
    """
    See class TreeProjectorBase.
    """
    def handle_sample(self, sample):
        self.message('INFO starting sample: ' + sample)

        n_procs = varial.settings.max_num_processes
        with varial.multiproc.WorkerPool(n_procs) as pool:
            for section, selection, weight in self.sec_sel_weight:
                if isinstance(weight, dict):
                    weight = weight[sample]
                res = self.prepare_mapiter(selection, weight, sample)
                res = pool.imap_unordered(mr.map_projection_per_file, res)
                res = itertools.chain.from_iterable(res)
                res = mr.reduce_projection(res, self.params)
                res = list(res)
                assert res, 'tree_projection did not yield any histograms'
                mr.store_sample(sample, section, res)

        varial.diskio.write_fileservice(sample)
        self.message('INFO sample done: ' + sample)

    def run(self):
        os.system('touch ' + self.cwd + 'webcreate_denial')
        self.hot_result = []

        n_procs = min(varial.settings.max_num_processes, len(self.samples))
        with varial.multiproc.WorkerPool(n_procs) as pool:
            res = ((varial.analysis.get_current_tool_path(), s)
                   for s in self.samples)

            # work
            res = pool.imap_unordered(_handle_sample, res)
            for _ in res:
                pass

        sample_func = lambda w: os.path.basename(w.file_path).split('.')[-2]
        if self.use_hot_result:
            wrps = varial.diskio.generate_aliases(self.cwd + '*.root')
            wrps = varial.gen.gen_add_wrp_info(wrps, sample=sample_func)
            self.hot_result = varial.diskio.bulk_load_histograms(wrps)
        else:
            self.put_aliases(sample_func)
