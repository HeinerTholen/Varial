#!/usr/bin/env python

"""
Just as e01_plot_root_files, but plots same hists into same canvases.

See the mk_rootfile_plotter call below.
"""

outdir = 'MyPlottedRootFilesCombined'

# set root to batch mode (it opens an x-connection otherwise)
import ROOT
ROOT.gROOT.SetBatch()

# import the tools module
import varial.tools

# get a plotter instance and run it (all arguments are optional)
pltr = varial.tools.mk_rootfile_plotter(
    name=outdir,        # output folder name
    combine_files=True  # YES to combine_files!!!
)

if __name__ == '__main__':
    pltr.run()                          # run the plotter
    varial.tools.WebCreator().run()     # run the WebCreator


def dummy_func():
    """This is a dummy to get a [source] link in the docs."""