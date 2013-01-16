from ROOT import TH1F
from cmstoolsac3b.test.test_histotoolsbase import TestHistoToolsBase
from cmstoolsac3b.wrappers import FileServiceAlias


class TestHistoDispatch(TestHistoToolsBase):
    def test_fileservice_aliases(self):
        aliases = self.dispatch.fileservice_aliases()

        # Is number of loaded elements correct?
        self.assertEqual(len(aliases), 150)

        # Are sample names correct?
        samples = set(a.sample for a in aliases)
        self.assertIn("tt", samples)
        self.assertIn("ttgamma", samples)
        self.assertIn("zjets", samples)

        # Check for some analyzers
        analyzers = set(a.analyzer for a in aliases)
        self.assertIn("realTemplate", analyzers)
        self.assertIn("analyzer_ET", analyzers)

        # Check for some histonames
        histos = set(a.name for a in aliases)
        self.assertIn("histo", histos)
        self.assertIn("sihihEB", histos)

    def test_load_histogram(self):
        test_alias = FileServiceAlias("cutflow", "analyzeSelection", "ttgamma")
        wrp = self.dispatch.load_histogram(test_alias)
        self.assertEqual(wrp.name, test_alias.name)
        self.assertEqual(wrp.analyzer, test_alias.analyzer)
        self.assertEqual(wrp.sample, test_alias.sample)
        self.assertIsInstance(wrp.histo, TH1F)
        self.assertAlmostEqual(wrp.histo.Integral(), 280555.0, delta=0.001)


import unittest
suite = unittest.TestLoader().loadTestsFromTestCase(TestHistoDispatch)
if __name__ == '__main__':
    unittest.main()