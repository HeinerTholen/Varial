import analysis
import diskio
import generators
import operations
import rendering
import settings
import wrappers

ana = analysis
gen = generators
op = operations
rnd = rendering
wrp = wrappers


def raise_root_error_level():
    import ROOT
    ROOT.gROOT.ProcessLine('gErrorIgnoreLevel = kError;')