#!/usr/bin/env python

"""
Basic analysis script. Execute me in the ``varial_examples`` directory.

Originally taken from https://github.com/HeinAtCERN/BTagDeltaR/blob/master/Analysis/python/varial_analysis.py
"""

# import and configure root
import ROOT
ROOT.gROOT.SetBatch()
ROOT.gROOT.ProcessLine('gErrorIgnoreLevel = kError;')

# import varial components
import varial.main

# these modules are also examples
import e04_sampledefinition         # sample definition
import e03_make_a_toolchain         # my normalization tool

# list of all samples
samples = e04_sampledefinition.smp_emu_mc + e04_sampledefinition.smp_emu_data

# all samples should be active, appart from plain TTbar
active_samples = list(s.name for s in samples)
active_samples.remove('TTbar')


# go for main
def main():
    """main"""
    varial.main.main(
        samples=samples,
        active_samples=active_samples,

        # the toolchain is just an example and has nothing to do with the
        # samples and settings in the respective examples
        toolchain=e03_make_a_toolchain.tc,
    )


if __name__ == '__main__':
    main()



