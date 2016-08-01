"""
Treeprojection on SGE with jug. (https://jug.readthedocs.org)
"""
from varial_ext.treeprojector import TreeProjectorBase
import varial_ext.treeprojection_mr_impl as mr
import pyspark
import varial
import os


############################################################ tree projector ###
class SparkTreeProjector(TreeProjectorBase):
    """
    Project histograms from files with TTrees on SGE with jug.

    Same args as TreeProjectorBase plus:
    :param spark_url:   e.g. spark://localhost:7077.
    """
    def __init__(self, *args, **kws):
        self.sc = kws.pop('spark_url', 'local')
        super(SparkTreeProjector, self).__init__(*args, **kws)

    def run(self):
        os.system('touch ' + self.cwd + 'webcreate_denial')
        if isinstance(self.sc, str):
            self.sc = pyspark.SparkContext(
                self.sc,
                'SparkTreeProjector/%s' % os.getlogin()
            )

        # do the work
        for section, selection, weight in self.sec_sel_weight:
            self.message('INFO starting section "%s"' % section)
            inputs = list(
                (
                    sample,
                    os.path.abspath(f),
                    self.prepare_params(selection, weight, sample)
                )
                for sample, filenames in self.filenames.iteritems()
                for f in filenames
            )
            rdd = self.sc.parallelize(inputs)
            rdd = rdd.flatMap(mr.map_projection_per_file)
            rdd = rdd.reduceByKey(lambda a,b: mr.plain_histo_sum(iter([a,b])))
            rdd = rdd.map(lambda x: (x[0].split()[0], x))
            rdd = rdd.groupByKey()
            res = rdd.collect()
            for sample, histo_iter in res:
                mr.store_sample(sample, section, histo_iter)
                varial.diskio.write_fileservice(sample, initial_mode='UPDATE')

        # finalize
        self.finalize(lambda w: os.path.basename(w.file_path).split('.')[-2])
