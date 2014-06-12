import os
from ROOT import TH1F
from test_histotoolsbase import TestHistoToolsBase
from varial.wrappers import FileServiceAlias
from varial import diskio
from varial import analysis

class TestDiskio(TestHistoToolsBase):

    def setUp(self):
        super(TestDiskio, self).setUp()
        if not os.path.exists("test_data"):
            os.mkdir("test_data")

    def test_fileservice_aliases(self):
        for name, smp in analysis.all_samples.items():
            analysis.fs_aliases += list(
                alias for alias in diskio.generate_fs_aliases(
                    'fileservice/%s.root' % name,
                    smp
                )
            )
        aliases = analysis.fs_aliases[:]

        # Is number of loaded elements correct?
        self.assertEqual(len(aliases), 150)

        # Are sample names correct?
        samples = set(a.sample for a in aliases)
        self.assertTrue("tt" in samples)
        self.assertTrue("ttgamma" in samples)
        self.assertTrue("zjets" in samples)

        # Check for some analyzers
        analyzers = set(a.analyzer for a in aliases)
        self.assertTrue("realTemplate" in analyzers)
        self.assertTrue("analyzer_ET" in analyzers)

        # Check for some histonames
        histos = set(a.name for a in aliases)
        self.assertTrue("histo" in histos)
        self.assertTrue("sihihEB" in histos)

    def test_load_histogram(self):
        test_alias = FileServiceAlias(
            "cutflow", "analyzeSelection", "fileservice/ttgamma.root",
            analysis.all_samples["ttgamma"]
        )
        wrp = diskio.load_histogram(test_alias)
        self.assertEqual(wrp.name, test_alias.name)
        self.assertEqual(wrp.analyzer, test_alias.analyzer)
        self.assertEqual(wrp.sample, test_alias.sample)
        self.assertTrue(isinstance(wrp.histo, TH1F))
        self.assertAlmostEqual(wrp.histo.Integral(), 280555.0)

    def test_write(self):
        fname = "test_data/wrp_save.info"
        diskio.write(self.test_wrp, fname)

        # file should exist
        self.assertTrue(
            os.path.exists(fname)
        )

        # file should have 7 lines (with history written out)
        with open(fname) as fhandle:
            n_lines = len(list(fhandle))
            self.assertEqual(n_lines, 21)

    def test_read(self):
        fname = "test_data/wrp_load.info"
        diskio.write(self.test_wrp, fname)
        loaded = diskio.read(fname)
        self.test_wrp.history = str(self.test_wrp.history)

        # check names
        self.assertEqual(
            self.test_wrp.all_writeable_info(),
            loaded.all_writeable_info()
        )

        # check histograms (same integral, different instance)
        self.assertEqual(self.test_wrp.histo.Integral(), loaded.histo.Integral())
        self.assertNotEqual(str(self.test_wrp.histo), str(loaded.histo))


import unittest
suite = unittest.TestLoader().loadTestsFromTestCase(TestDiskio)
if __name__ == '__main__':
    unittest.main()