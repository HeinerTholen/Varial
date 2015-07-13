#!/usr/bin/env python

import os
from ROOT import TH1F
from test_histotoolsbase import TestHistoToolsBase
from varial.wrappers import FileServiceAlias, HistoWrapper, WrapperWrapper
from varial import diskio
from varial import analysis

class TestDiskio(TestHistoToolsBase):

    def setUp(self):
        super(TestDiskio, self).setUp()
        if not os.path.exists('test_data'):
            os.mkdir('test_data')

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
        self.assertTrue('tt' in samples)
        self.assertTrue('ttgamma' in samples)
        self.assertTrue('zjets' in samples)

        # Check for some in_file_path
        ifps = set(a.in_file_path for a in aliases)
        self.assertIn('realTemplate/sihihEB', ifps)
        self.assertIn('analyzer_ET/photonET', ifps)

        # Check for some histonames
        histos = set(a.name for a in aliases)
        self.assertTrue('histo' in histos)
        self.assertTrue('sihihEB' in histos)

    def test_load_histogram(self):
        test_alias = FileServiceAlias(
            'fileservice/ttgamma.root',
            'analyzeSelection/cutflow',
            'TH1D',
            analysis.all_samples['ttgamma']
        )
        wrp = diskio.load_histogram(test_alias)
        self.assertEqual(wrp.name, test_alias.name)
        self.assertEqual(wrp.in_file_path, test_alias.in_file_path)
        self.assertEqual(wrp.sample, test_alias.sample)
        self.assertTrue(isinstance(wrp.histo, TH1F))
        self.assertAlmostEqual(wrp.histo.Integral(), 280555.0)

    def test_write(self):
        fname = 'test_data/wrp_save.info'
        diskio.write(self.test_wrp, fname)

        # file should exist
        self.assertTrue(
            os.path.exists(fname)
        )

        # file should have a couple of lines (with history written out)
        with open(fname) as fhandle:
            n_lines = len(list(fhandle))
            self.assertGreater(n_lines, 10)

    def test_read(self):
        fname = 'test_data/wrp_load.info'
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

    def test_write_wrpwrp(self):
        fname = 'test_data/wrpwrp_save.info'
        wrpwrp1 = WrapperWrapper([
            HistoWrapper(TH1F('h1', 'h1', 2, 0, 2)),
            HistoWrapper(TH1F('h2', 'h2', 2, 0, 2)),
        ])
        diskio.write(wrpwrp1, fname)

        # check written data
        with open(fname) as fhandle:
            n_lines = len(list(fhandle))
            self.assertGreater(n_lines, 4)

        # check written wrapper
        self.assertTrue(isinstance(wrpwrp1.wrps[0], HistoWrapper))

    def test_read_wrpwrp(self):
        fname = 'test_data/wrpwrp_load'
        wrpwrp1 = WrapperWrapper([
            HistoWrapper(TH1F('h3', 'h3', 2, 0, 2)),
            HistoWrapper(TH1F('h4', 'h4', 2, 0, 2)),
        ])
        wrpwrp1.wrps[0].histo.Fill(0.5)
        wrpwrp1.wrps[1].histo.Fill(1.5)
        diskio.write(wrpwrp1, fname)

        wrpwrp2 = diskio.read(fname)
        self.assertAlmostEqual(wrpwrp2.wrps[0].histo.GetBinContent(1), 1.)
        self.assertAlmostEqual(wrpwrp2.wrps[0].histo.GetBinContent(2), 0.)
        self.assertAlmostEqual(wrpwrp2.wrps[1].histo.GetBinContent(1), 0.)
        self.assertAlmostEqual(wrpwrp2.wrps[1].histo.GetBinContent(2), 1.)


import unittest
suite = unittest.TestLoader().loadTestsFromTestCase(TestDiskio)
if __name__ == '__main__':
    unittest.main()