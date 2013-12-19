import os
import varial.generators as gen
from ROOT import TH1F, TFile
from test_histotoolsbase import TestHistoToolsBase
from varial.wrappers import \
    StackWrapper, \
    HistoWrapper
import varial.settings as settings

class TestGenerators(TestHistoToolsBase):
    def tearDown(self):
        super(TestGenerators, self).tearDown()
        if hasattr(self, "tfile"):
            self.tfile.Close()
            del self.tfile

    def test_gen_fs_content(self):
        aliases = list(gen.fs_content())
        self.assertEqual(len(aliases), 150)

    def test_gen_load(self):
        aliases       = gen.fs_content()
        zjets_cutflow = gen.filter(aliases, {"name": "cutflow", "sample":"zjets"})
        wrp           = gen.load(zjets_cutflow).next()
        self.assertTrue(isinstance(wrp.histo, TH1F))
        self.assertAlmostEqual(wrp.histo.Integral(), 2889.0)

    def test_gen_save(self):
        wrps = gen.fs_filter_sort_load({
            "name": "cutflow",
            "sample":["zjets","ttgamma"]
        })

        # create dir and go
        if not os.path.exists("test"):
            os.mkdir("test")
        gen.consume_n_count(
            gen.save(
                wrps,
                lambda w: "test/"+w.name+"_"+w.sample
            )
        )

        # check the new files
        self.assertTrue(os.path.exists("test/cutflow_ttgamma.root"))
        self.assertTrue(os.path.exists("test/cutflow_ttgamma.info"))
        self.assertTrue(os.path.exists("test/cutflow_zjets.root"))
        self.assertTrue(os.path.exists("test/cutflow_zjets.info"))
        self.tfile = TFile.Open("test/cutflow_ttgamma.root")
        self.assertTrue(self.tfile.GetKey("histo"))

    def test_gen_filter(self):
        import re
        aliases  = list(gen.fs_content())
        data     = gen.filter(aliases, {"is_data": True})
        tmplt    = gen.filter(aliases, {"analyzer": "fakeTemplate"})
        crtlplt  = gen.filter(aliases, {"analyzer": re.compile("CrtlFilt*")})
        crtlplt2 = gen.filter(aliases, {"analyzer": [re.compile("CrtlFilt*")]})
        ttgam_cf = gen.filter(aliases,
            {
                "name": "cutflow",
                "sample": ["ttgamma", "tt"]
            }
        )
        self.assertEqual(gen.consume_n_count(data), 52)
        self.assertEqual(gen.consume_n_count(tmplt), 9)
        self.assertEqual(gen.consume_n_count(crtlplt), 39)
        self.assertEqual(gen.consume_n_count(crtlplt2), 39)
        self.assertEqual(gen.consume_n_count(ttgam_cf), 2)

    def test_gen_special_treat(self):
        sample = ["tt","zjets"]
        name = "cutflow"
        class TreatCls(object):
            def __init__(self, test):
                self.test = test
                self.n_times_called = 0
            def __call__(self, alias):
                self.n_times_called += 1
                self.test.assertTrue(alias.sample in sample)
                self.test.assertEqual(alias.name, name)
        treat_func = TreatCls(self)
        treated = gen.callback(
            gen.fs_content(),
            treat_func,
            {"sample":sample, "name":name}
        )
        self.assertEqual(gen.consume_n_count(treated), 150)
        self.assertEqual(treat_func.n_times_called, 2)

    def test_gen_sort(self):
        aliases      = list(gen.fs_content())
        tmplt        = gen.filter(aliases, {"analyzer": "fakeTemplate"})
        sorted       = list(gen.sort(tmplt))
        s_name       = map(lambda x:x.name, sorted)
        s_sample     = map(lambda x:x.sample, sorted)
        s_is_data    = map(lambda x:x.is_data, sorted)
        self.assertTrue(s_sample.index("ttgamma") < s_sample.index("zjets"))
        self.assertTrue(s_name.index("sihihEB") < s_name.index("sihihEE"))
        self.assertTrue(s_is_data.index(False) < s_is_data.index(True))

    def test_gen_group(self):
        from_fs  = gen.fs_content()
        filtered = gen.filter(from_fs, {"name":"histo"})
        sorted   = gen.sort(filtered)
        grouped  = gen.group(sorted)
        group_list = []
        for group in grouped:
            group_list.append(list(group))

        # length: 3 samples: 3 histos per group
        self.assertEqual(len(group_list), 26)
        for g in group_list:
            self.assertEqual(len(g), 3)
            self.assertEqual(g[0].analyzer, g[1].analyzer)
            self.assertEqual(g[0].analyzer, g[2].analyzer)

    def test_gen_fs_filter_sort_load(self):
        wrps = list(gen.fs_filter_sort_load({
            "name": "cutflow",
            "sample": ["ttgamma", "tt"]
        }))
        s_is_data = map(lambda x: x.is_data, wrps)

        # just check for sorting and overall length
        self.assertTrue(s_is_data.index(False) < s_is_data.index(True))
        self.assertEqual(len(wrps), 2)
        self.assertEqual(wrps[1].lumi, 3.0)

    def test_gen_fs_mc_stack_n_data_sum(self):
        res = gen.fs_mc_stack_n_data_sum(
            {"name": "histo"}
        )
        mc, data = res.next()

        # correct instances
        self.assertTrue(isinstance(mc, StackWrapper))
        self.assertTrue(isinstance(data, HistoWrapper))

        # ... of equal lumi (from data)
        self.assertEqual(mc.lumi, settings.data_samples()["tt"].lumi)
        self.assertEqual(data.lumi, settings.data_samples()["tt"].lumi)

        # check stacking order by history
        h = str(mc.history)
        self.assertTrue(h.index("ttgamma") < h.index("zjets"))
        settings.stacking_order.reverse()
        mc, data = res.next()
        h = str(mc.history)
        self.assertTrue(h.index("zjets") < h.index("ttgamma"))

#    # THIS TEST SEEMS TO FIND A ROOT BUG:
#    def test_gen_canvas(self):
#        stk, dat = gen.fs_mc_stack_n_data_sum().next()
#        canvas = gen.canvas([(stk, dat)])
#        cnv = next(canvas)
#
#        # check for stack and data to be in canvas primitives
#        prim = cnv.canvas.GetListOfPrimitives()
#        self.assertIn(stk.stack, prim)
#        self.assertIn(stk.histo, prim)
#        self.assertIn(dat.histo, prim)
#        del stk
#        del dat


import unittest
suite = unittest.TestLoader().loadTestsFromTestCase(TestGenerators)
if __name__ == '__main__':
    unittest.main()