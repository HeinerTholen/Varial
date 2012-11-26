import os
from cmstoolsac3b.test.test_histotoolsbase import TestHistoToolsBase
from cmstoolsac3b.wrappers import HistoWrapper

class TestWrapper(TestHistoToolsBase):
    def setUp(self):
        super(TestWrapper, self).setUp()
        if not os.path.exists("test"):
            os.mkdir("test")

    def test_write_info_file(self):
        fname = "test/wrp_save.info"
        self.test_wrp.write_info_file(fname)
        self.assertTrue(
            os.path.exists(fname)
        )

    def test_create_from_file(self):
        fname = "test/wrp_load.info"
        self.test_wrp.write_info_file(fname)
        loaded = HistoWrapper.create_from_file(
            fname,
            self.test_wrp.histo
        )
        self.test_wrp.history = repr(str(self.test_wrp.history))
        self.assertDictEqual(
            self.test_wrp.__dict__,
            loaded.__dict__
        )

import unittest
suite = unittest.TestLoader().loadTestsFromTestCase(TestWrapper)
if __name__ == '__main__':
    unittest.main()