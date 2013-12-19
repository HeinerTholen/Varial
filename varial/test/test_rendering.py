import os
from ROOT import TCanvas
from test_histotoolsbase import TestHistoToolsBase
from varial.rendering import CanvasBuilder
from varial.wrappers import HistoWrapper
import varial.diskio as diskio

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
        self.assertTrue(wrp1.histo in prim)
        self.assertTrue(wrp2.histo in prim)
        self.test_wrp = wrp

    def test_canvas_info_file(self):
        fname = "test/cnv_save.info"
        self.test_canvasBuilder_make()
        diskio.write(self.test_wrp, fname)

        # file should have 23 lines (with history written out)
        with open(fname) as fhandle:
            self.assertEqual(len(list(fhandle)), 23)


import unittest
suite = unittest.TestLoader().loadTestsFromTestCase(TestRendering)
if __name__ == '__main__':
    unittest.main()