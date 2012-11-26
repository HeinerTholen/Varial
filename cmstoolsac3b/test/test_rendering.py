from cmstoolsac3b.test.test_histotoolsbase import TestHistoToolsBase
from cmstoolsac3b.rendering import CanvasBuilder
from cmstoolsac3b.wrappers import HistoWrapper
from ROOT import TCanvas

class TestRendering(TestHistoToolsBase):

    def test_canvasBuilder_make(self):
        wrp1 = self.test_wrp
        wrp2 = HistoWrapper(wrp1.histo)
        wrp2.histo.Scale(1.5)
        cb = CanvasBuilder((wrp1, wrp2))
        wrp = cb.build_canvas()

        # check for stack and data to be in canvas primitives
        prim = wrp.canvas.GetListOfPrimitives()
        self.assertIn(wrp1.histo, prim)
        self.assertIn(wrp2.histo, prim)
        del wrp


import unittest
suite = unittest.TestLoader().loadTestsFromTestCase(TestRendering)
if __name__ == '__main__':
    unittest.main()