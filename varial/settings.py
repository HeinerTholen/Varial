"""
This module contains project wide settings.
"""
################################################################### general ###
import time

tweak           = "tweak.py"
logfilename     = time.strftime(
    "cmstoolsac3b_%Y%m%dT%H%M%S.log", 
    time.localtime()
)

################################################################ processing ###
import multiprocessing

max_num_processes       = multiprocessing.cpu_count()
not_ask_execute         = False
suppress_cmsRun_exec    = False
try_reuse_results       = False
default_enable_sample   = True
cfg_main_import_path    = ""
cfg_use_file_service    = True
cfg_output_module_name  = "out"
cfg_common_builtins     = {}

cmsRun_procs = []
controller   = None

########################################################### post-processing ###
post_proc_tools         = []
postprocessor           = None
web_target_dir          = ""
tex_target_dir          = ""
plot_target_dir         = ""
enable_postproc_reuse   = True
box_text_size           = 0.037
defaults_Legend         = {
    "x_pos"         : 0.92,
    "y_pos"         : 0.83,
    "label_width"   : 0.24,
    "label_height"  : 0.04,
    "opt"           : "f",
    "opt_data"      : "p",
    "reverse"       : True
}
defaults_BottomPlot     = {
    "y_title"   : "Data/MC",
    "draw_opt"  : "E1",
    "x_min"     : 0.,
    "x_max"     : 3.,
}
histo_pool              = []
post_proc_dict          = {} # Data storage for post proc tools
persistent_dict         = {} # PostProcChainSystematics will not touch this.
persistent_data         = [  # PostProcChainSystematics will not touch these.
    "cmsRun_procs",
    "controller",
    "post_proc_tools",
    "postprocessor",
    "persistent_dict",
    "persistent_data",
    "stack_dir_result",
    "stack_dir_pstprc"
    "gROOT",
    "StyleClass",
    "TStyle",
    "TGaxis",
    "root_style",
]
#TODO split into settings (static stuff) and config (variable stuff)

################################################################### samples ###
import wrappers as wrp

samples = {}        # all samples being processed
active_samples = [] # list of strings of samplenames (without systematic smpls)
def mc_samples():
    """Returns a dict of all MC samples."""
    return dict(
        (k,v)
        for k,v in samples.iteritems()
        if k in active_samples and not v.is_data
    )

def data_samples():
    """Returns a dict of all real data samples."""
    return dict(
        (k,v)
        for k,v in samples.iteritems()
        if k in active_samples and v.is_data
    )

def data_lumi_sum():
    """Returns the sum of luminosity in data samples."""
    return float(sum(
        v.lumi
        for k,v in data_samples().iteritems()
        if k in active_samples
    ))

def data_lumi_sum_wrp():
    """Returns the sum of data luminosity in as a FloatWrapper."""
    return wrp.FloatWrapper(data_lumi_sum(), history="DataLumiSum")

######################################################### folder management ###
import os
import sys

DIR_WORKING = "./"
dir_result = DIR_WORKING
stack_dir_result = [DIR_WORKING]


def push_tool_dir(name):
    stack_dir_result.append(name)
    _set_dir_vars()


def pop_tool_dir():
    stack_dir_result.pop()
    _set_dir_vars()


def create_folder(path):
    if not os.path.exists(path):
        os.mkdir(path)


def create_folders():
    """Create all "DIR" prefixed folders."""
    this_mod = sys.modules[__name__]
    for name in dir(this_mod):
        if name[0:3] == "DIR":
            path = getattr(this_mod, name)
            create_folder(path)


def _set_dir_vars():
    this_mod = sys.modules[__name__]
    this_mod.dir_result = "/".join(stack_dir_result) + "/"

########################################################### style constants ###
canvas_size_x = 800
canvas_size_y = 800

rootfile_postfixes = [".root"]

pretty_names = {}
def get_pretty_name(key):
    """Simple dict call for names, e.g. axis labels."""
    return pretty_names.get(key, key)

colors = {} # map legend entries to fill colors
def get_color(sample_or_legend_name):
    """Gives a ROOT color value back for sample or legend name."""
    if colors.has_key(sample_or_legend_name):
        return colors[sample_or_legend_name]
    elif samples.has_key(sample_or_legend_name):
        return colors.get(samples[sample_or_legend_name].legend)

stacking_order = []
def get_stack_position(sample):
    """Returns the stacking position (integer)"""
    legend = samples[sample].legend
    if legend in stacking_order:
        return str(stacking_order.index(legend) * 0.001)  # print enough digits
    else:
        return legend

################################################################ root style ###
from ROOT import gROOT, TStyle, TGaxis

class StyleClass(TStyle):
    """
    Sets all ROOT style variables.
    Places self as new ROOT style.
    """
    def __init__(self):
        super(StyleClass, self).__init__("CRRootStyle", "CRRootStyle")
        self.root_style_settings()
        self.cd()
        gROOT.SetStyle("CRRootStyle")
        gROOT.ForceStyle()
        TGaxis.SetMaxDigits(3)

    def root_style_settings(self):
        """
        All custom style settings are specified here and applied to self.
        """
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
        self.SetPadRightMargin(0.04)
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

root_style = StyleClass() #! reference to the TStyle class instance.
