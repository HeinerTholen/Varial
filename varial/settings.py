"""
This module contains project wide settings.
"""


################################################################### general ###
import os
import time
recieved_sigint = False
only_reload_results = False
varial_working_dir = "./"
db_name = '.varial.db'
default_data_lumi = 1.
default_colors = [632, 878, 596, 870, 434, 840, 902, 417, 828, 618, 400, 800]
wrp_sorting_keys = ['analyzer', 'name', 'is_data', 'sample']


def logfilename():
    return time.strftime(
        os.path.join(varial_working_dir,
                     ".varial_logs/varial_%Y%m%dT%H%M%S.log"),
        time.localtime()
    )


############################################## cmsRun and fwlite processing ###
import multiprocessing
max_num_processes = multiprocessing.cpu_count()
not_ask_execute = False
suppress_eventloop_exec = False
try_reuse_results = True
force_reuse_fwlite = False
default_enable_sample = True
fwlite_profiling = False


########################################################### style constants ###
canvas_size_x = 800
canvas_size_y = 800

box_text_size = 0.037
defaults_Legend = {
    "x_pos": 0.92,
    "y_pos": 0.83,
    "label_width": 0.24,
    "label_height": 0.04,
    "opt": "f",
    "opt_data": "p",
    "reverse": True
}
defaults_BottomPlot = {
    "y_title": "#frac{Data-MC}{MC}",
    "draw_opt": "E1",
    "x_min": -1.,
    "x_max": 1.,
}

rootfile_postfixes = [".root"]
colors = {}  # legend entries => fill colors
pretty_names = {}
stacking_order = []


################################################################ root style ###
from array import array
from ROOT import gROOT, gStyle, TColor, TStyle, TGaxis


class StyleClass(TStyle):
    """
    Sets all ROOT style variables.
    Places self as new ROOT style.
    """
    def __init__(self):
        super(StyleClass, self).__init__("CmsRootStyle", "CmsRootStyle")

        ################################ custom root style commands ###
        self.SetFrameBorderMode(0)
        self.SetCanvasBorderMode(0)
        self.SetPadBorderMode(0)
        self.SetPadBorderMode(0)

        #self.SetFrameColor(0)
        self.SetPadColor(0)
        self.SetCanvasColor(0)
        self.SetStatColor(0)
        self.SetFillColor(0)
        self.SetNdivisions(505, "XY")

        self.SetPaperSize(20, 26)
        #self.SetPadTopMargin(0.08)
        #self.SetPadBottomMargin(0.14)
        self.SetPadRightMargin(0.16)
        self.SetPadLeftMargin(0.16)
        #self.SetCanvasDefH(800)
        #self.SetCanvasDefW(800)
        #self.SetPadGridX(1)
        #self.SetPadGridY(1)
        self.SetPadTickX(1)
        self.SetPadTickY(1)

        self.SetTextFont(42) #132
        self.SetTextSize(0.09)
        self.SetLabelFont(42, "xyz")
        self.SetTitleFont(42, "xyz")
        self.SetLabelSize(0.045, "xyz") #0.035
        self.SetTitleSize(0.045, "xyz")
        self.SetTitleOffset(1.3, "xy")

        self.SetTitleX(0.16)
        self.SetTitleY(0.93)
        self.SetTitleColor(1)
        self.SetTitleTextColor(1)
        self.SetTitleFillColor(0)
        self.SetTitleBorderSize(1)
        self.SetTitleFontSize(0.04)
        #self.SetPadTopMargin(0.05)
        self.SetPadBottomMargin(0.13)
        #self.SetPadLeftMargin(0.14)
        #self.SetPadRightMargin(0.02)

        # use bold lines and markers
        self.SetMarkerStyle(8)
        self.SetMarkerSize(1.2)
        self.SetHistLineWidth(1)
        self.SetLineWidth(1)

        self.SetOptTitle(1)
        self.SetOptStat(0)

        # don't know what these are for. Need to ask the kuess'l-o-mat.
        self.colors = [1, 2, 3, 4, 6, 7, 8, 9, 11]
        self.markers = [20, 21, 22, 23, 24, 25, 26, 27, 28]
        self.styles = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        ############################ end custom root style commands ###

        self.cd()
        self.set_palette()
        gROOT.SetStyle("CmsRootStyle")
        gROOT.ForceStyle()
        TGaxis.SetMaxDigits(3)

    @staticmethod
    def set_palette(name='', ncontours=999):
        if name == "gray" or name == "grayscale":
            stops = [0.00, 0.34, 0.61, 0.84, 1.00]
            red   = [1.00, 0.84, 0.61, 0.34, 0.00]
            green = [1.00, 0.84, 0.61, 0.34, 0.00]
            blue  = [1.00, 0.84, 0.61, 0.34, 0.00]
        else:
            # default palette, looks cool
            stops = [0.00, 0.34, 0.61, 0.84, 1.00]
            red   = [0.00, 0.00, 0.87, 1.00, 0.51]
            green = [0.00, 0.81, 1.00, 0.20, 0.00]
            blue  = [0.51, 1.00, 0.12, 0.00, 0.00]

        s = array('d', stops)
        r = array('d', red)
        g = array('d', green)
        b = array('d', blue)

        npoints = len(s)
        TColor.CreateGradientColorTable(npoints, s, r, g, b, ncontours)
        gStyle.SetNumberContours(ncontours)

root_style = StyleClass()  
