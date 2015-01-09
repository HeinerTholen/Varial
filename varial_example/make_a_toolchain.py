"""
Example on making a toolchain.

Originally taken from https://github.com/HeinAtCERN/BTagDeltaR/blob/master/Analysis/python/varial_analysis.py
"""

import varial.tools
import make_a_tool

# fwlite script to run over events
fwlite_exe = 'BTagDeltaR/Analysis/python/worker_vertexDR.py'

# setup the base toolchain
# (the constructor takes a name string and a list of tools)
tc = varial.tools.ToolChain(
    "EXAMPLE_ANALYSIS",
    [
        # You can make a fwlite job like this:
        # varial.tools.FwliteProxy(fwlite_exe),
        # But for now we simply copy the test fileservice directory
        varial.tools.CopyTool(
            src='../varial/test/fileservice',
            dest='.',
            wipe_dest_dir=False  # do not wipe dest dir!
        ),

        # use the histo normalizer example
        make_a_tool.MyHistoNormalizer(lambda w: w.name == 'MyHisto'),

        # simply plot everything we can find
        varial.tools.mk_rootfile_plotter('all_plots'),

        # website output
        varial.tools.WebCreator(),

        # copy webcontent to a place where the webserver can find it
        # varial.tools.CopyTool(os.path.join(os.environ['HOME'], 'www/ana/')),
    ]
)


def dummy_func():
    """
    This is just a dummy to include a [source] link in the doc.
    """
