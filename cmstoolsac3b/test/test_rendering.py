import os
from cmstoolsac3b.test.test_histotoolsbase import TestHistoToolsBase
from cmstoolsac3b.rendering import CanvasBuilder
from cmstoolsac3b.wrappers import HistoWrapper
from ROOT import TCanvas

class TestRendering(TestHistoToolsBase):
    def setUp(self):
        super(TestRendering, self).setUp()
        if not os.path.exists("test"):
            os.mkdir("test")

    def test_canvasBuilder_make(self):
        wrp1 = self.test_wrp
        wrp2 = HistoWrapper(wrp1.histo, history="Fake history")
        wrp2.histo.Scale(1.5)
        cb = CanvasBuilder((wrp1, wrp2))
        wrp = cb.build_canvas()

        # check for stack and data to be in canvas primitives
        prim = wrp.canvas.GetListOfPrimitives()
        self.assertIn(wrp1.histo, prim)
        self.assertIn(wrp2.histo, prim)
        self.test_wrp = wrp
        self.fail()

    def test_canvas_info_file(self):
        fname = "test/cnv_save.info"
        self.test_canvasBuilder_make()
        self.test_wrp.write_info_file(fname)
        # file should have 6 lines (with history written out)
        n_lines = 0
        with open(fname) as fhandle:
            for line in fhandle:
                n_lines += 1
        self.assertEqual(n_lines, 6)


import unittest
suite = unittest.TestLoader().loadTestsFromTestCase(TestRendering)
if __name__ == '__main__':
    unittest.main()