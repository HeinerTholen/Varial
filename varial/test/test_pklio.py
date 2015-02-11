#!/usr/bin/env python

import cPickle
import os
from test_histotoolsbase import TestHistoToolsBase
from varial import pklio
from varial import analysis


class TestPklio(TestHistoToolsBase):
    def setUp(self):
        super(TestPklio, self).setUp()
        if not os.path.exists('test_data'):
            os.mkdir('test_data')
        analysis.cwd = 'test_data'

    def tearDown(self):
        analysis.cwd = ''
        super(TestPklio, self).tearDown()

    def test_write(self):
        pklio.write(self.test_wrp)
        pklio._write_out()

        # check existance
        self.assertTrue(os.path.exists('test_data/data.pkl'))
        if os.path.exists('test_data/data.pkl'):
            with open('test_data/data.pkl') as f:
                obj = cPickle.load(f)
            self.assertTrue(type(obj) == dict)
            self.assertIn(self.test_wrp.name, obj)

    def test_read(self):
        self.test_wrp.history = str(self.test_wrp.history)
        pklio.write(self.test_wrp)

        # distract pklio a little and load
        analysis.cwd = 'blob'
        pklio._sync()
        analysis.cwd = 'test_data'
        loaded = pklio.read(self.test_wrp.name)

        # check names
        self.assertEqual(
            self.test_wrp.all_writeable_info(),
            loaded.all_writeable_info()
        )

        # check histograms (same integral, different instance)
        self.assertEqual(self.test_wrp.histo.Integral(),loaded.histo.Integral())
        self.assertNotEqual(str(self.test_wrp.histo), str(loaded.histo))

        # check error
        self.assertRaises(RuntimeError, pklio.read, "non_existent")


import unittest
suite = unittest.TestLoader().loadTestsFromTestCase(TestPklio)
if __name__ == '__main__':
    unittest.main()