import ROOT
#ROOT.gROOT.SetBatch()

import diskio
import generators
import gridutil
import operations
import postprocessing
import postproctools
import rendering
import sample
import settings
import wrappers

for member in dir(settings):
    if member[:4] == "DIR_":
        setattr(settings, member, "./")
