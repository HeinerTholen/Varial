import ROOT
#ROOT.gROOT.SetBatch()

import settings
for member in dir(settings):
    if member[:4] == "DIR_":
        setattr(settings, member, "./")

import generators as gen
import operations as op
import wrappers as wrp
import diskio as dio