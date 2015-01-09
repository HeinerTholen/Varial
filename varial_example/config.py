#!/usr/bin/env python

"""
Basic analysis script. Does not actually work. But shows what can be done.

Originally taken from https://github.com/HeinAtCERN/BTagDeltaR/blob/master/Analysis/python/varial_analysis.py
"""

# import and configure root
import ROOT
ROOT.gROOT.SetBatch()
ROOT.gROOT.ProcessLine('gErrorIgnoreLevel = kError;')

# import varial components
import os
import varial.main
import varial.tools
import varial.settings as s

# these modules were in the same package
import sampledefinition     # sample definition
import make_a_tool          # my normalization tool

# set postfixes, that histograms should be stored with
s.rootfile_postfixes = ['.root', '.png', '.eps']

# fwlite script to run over events
fwlite_exe = 'BTagDeltaR/Analysis/python/worker_vertexDR.py'

# list of all samples
samples = sampledefinition.smp_emu_mc + sampledefinition.smp_emu_data

# all samples should be active, appart from plain TTbar
active_samples = list(s.name for s in samples)
active_samples.remove('TTbar')

# setup the base toolchain
tc = varial.tools.ToolChain(
    "ttdilep_analysis",
    [
        varial.tools.FwliteProxy(fwlite_exe),
        make_a_tool.MyHistoNormalizer(lambda w: w.name == 'MyHisto'),
        varial.tools.WebCreator(),
        varial.tools.CopyTool(os.path.join(os.environ['HOME'], 'www/btagdr/ana/')),
    ]
)


# go for main
def main():
    """main"""
    varial.main.main(
        samples=samples,
        active_samples=active_samples,
        toolchain=tc,
    )


if __name__ == '__main__':
    main()



