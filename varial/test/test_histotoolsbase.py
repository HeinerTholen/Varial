import unittest
import os
import shutil
from ROOT import TH1I, gROOT, kRed, kBlue
import varial.settings as settings
import varial.diskio as diskio
import varial.sample as sample
from varial.history import History
from varial.wrappers import HistoWrapper

class TestHistoToolsBase(unittest.TestCase):
    def setUp(self):
        super(TestHistoToolsBase, self).setUp()

        test_fs = "fileservice/"
        settings.DIR_FILESERVICE = test_fs
        if (not os.path.exists(test_fs + "tt.root")) \
        or (not os.path.exists(test_fs + "ttgamma.root")) \
        or (not os.path.exists(test_fs + "ttgamma.root")):
            self.fail("Fileservice testfiles not present!")

        # create samples
        settings.samples["tt"] = sample.Sample(
            name = "tt",
            is_data = True,
            lumi = 3.,
            legend = "pseudo data",
            input_files = ["none"],
        )
        settings.samples["ttgamma"] = sample.Sample(
            name = "ttgamma",
            lumi = 4.,
            legend = "tt gamma",
            input_files = ["none"],
        )
        settings.samples["zjets"] = sample.Sample(
            name = "zjets",
            lumi = 0.1,
            legend = "z jets",
            input_files = ["none"],
        )
        settings.colors = {
            "tt gamma": kRed,
            "z jets": kBlue
        }
        settings.stacking_order = [
            "tt gamma",
            "z jets"
        ]
        settings.active_samples = settings.samples.keys()

        #create a test wrapper
        h1 = TH1I("h1", "H1", 2, .5, 4.5)
        h1.Fill(1)
        h1.Fill(3,2)
        hist = History("test_op") # create some fake history
        hist.add_args([History("fake_input_A"), History("fake_input_B")])
        hist.add_kws({"john":"cleese"})
        self.test_wrp = HistoWrapper(
            h1,
            name="Nam3",
            title="T1tl3",
            history=hist
        )

    def tearDown(self):
        super(TestHistoToolsBase, self).tearDown()

        if os.path.exists("test"):
            shutil.rmtree("test")

        del self.test_wrp

        diskio.close_open_root_files()
        gROOT.Reset()

