"""
Treeprojection on SGE with jug. (https://jug.readthedocs.org)
"""
from varial_ext.treeprojector import TreeProjectorBase
import varial_ext.treeprojection_mr_impl as mr
import pyspark
import varial
import os


spark_context = None


def add_histos(a, b):
    c = a.Clone()
    c.Add(b)
    return c


def load_trees(args):
    import ROOT
    sample, treename, filename = args
    f = ROOT.TFile(os.path.abspath(filename))
    t = f.Get(treename)
    assert t, 'could not load tree; treename, file: %s, %s' % (treename, f)
    assert t.GetTotBytes() < 1.5e9, 'this tree is too large (1.5G allowed); size, treename, file:'\
                                    ' %iM, %s, %s' % (t.GetTotBytes()/1e6, treename, f)
    t.LoadBaskets()
    t.SetDirectory(0)
    f.Close()
    return sample, filename, t


def map_projection_spark(args, ssw, params):
    sample, filename, open_tree = args
    _, selection, weight = ssw
    params = dict(params)
    params['weight'] = weight[sample] if isinstance(weight, dict) else weight
    params['selection'] = selection
    histos = params['histos'].keys()

    map_iter = (res
                for h in histos
                for res in mr.map_projection(
                    '%s %s %s'%(sample, h, filename), params, None, open_tree))
    result = list(map_iter)

    return result


############################################################ tree projector ###
class SparkTreeProjector(TreeProjectorBase):
    """
    Project histograms from files with TTrees on SGE with jug.

    Same args as TreeProjectorBase plus:
    :param spark_url:   e.g. spark://localhost:7077.
    """
    def __init__(self, *args, **kws):
        global spark_context
        spark_context = pyspark.SparkContext(
            kws.pop('spark_url', 'local'),
            'SparkTreeProjector/%s' % os.getlogin()
        )
        self.rdd_cache = None
        super(SparkTreeProjector, self).__init__(*args, **kws)

    def run(self):
        os.system('touch ' + self.cwd + 'webcreate_denial')

        if True:  # not self.rdd_cache:
            self.message('INFO initializing root files.')
            treename = self.params['treename']
            inputs = list(
                (sample, treename, f)
                for sample, filenames in self.filenames.iteritems()
                for f in filenames
            )
            rdd = spark_context.parallelize(inputs)
            rdd = rdd.map(load_trees)
            # rdd.cache()
            self.rdd_cache = rdd

        # do the work
        params = self.params
        for ssw in self.sec_sel_weight:
            section = ssw[0]
            self.message('INFO starting section "%s".' % section)
            rdd = self.rdd_cache.flatMap(lambda args: map_projection_spark(args, ssw, params))
            rdd = rdd.reduceByKey(add_histos)
            rdd = rdd.map(lambda x: (x[0].split()[0], x))
            rdd = rdd.groupByKey()
            res = rdd.collect()
            for sample, histo_iter in res:
                mr.store_sample(sample, section, histo_iter)
                varial.diskio.write_fileservice(section+'.'+sample, initial_mode='UPDATE')

        # finalize
        self.finalize(lambda w: os.path.basename(w.file_path).split('.')[-2])
