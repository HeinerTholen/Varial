import ROOT
#ROOT.gROOT.SetBatch()

import settings
for member in dir(settings):
    if member[:4] == "DIR_":
        setattr(settings, member, "./")

