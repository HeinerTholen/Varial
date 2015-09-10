import analysis
import diskio
import generators
import monitor
import operations
import rendering
import settings
import wrappers

ana = analysis
gen = generators
op = operations
rnd = rendering
wrp = wrappers

import ROOT

def raise_root_error_level():
    ROOT.gROOT.ProcessLine('gErrorIgnoreLevel = kError;')