"""
Settings example from an analysis.
"""


def dummy_func():
    """
    This is just a dummy to include this source file in the doc.
    """

from varial import settings as s

# Postfixes. Default is only ".root"
s.rootfile_postfixes += [".png", ".eps"]

# Defines the order in which samples are stacked. Use legend entries.
s.stacking_order = [
    "t#bar{t}#gamma #mu+Jets (Signal)",
    "t#bar{t}#gamma (Signal)",
    "t#bar{t} inclusive",
    "W + Jets",
    "Z + Jets",
    "Single Top",
    "QCD",
    "q_{top} = 4/3"
]

# Coloring of filled histograms.
# See also histotools.generators.apply_fillcolor(wrps)
import ROOT
s.colors.update({
    "t#bar{t}#gamma #mu+Jets (Signal)"  : ROOT.kRed + 1,
    "t#bar{t}#gamma (Signal)"           : ROOT.kRed + 1,
    "t#bar{t} inclusive"                : ROOT.kAzure + 7,
    "W + Jets"                          : ROOT.kSpring + 8,
    "Z + Jets"                          : ROOT.kSpring + 5,
    "Single Top"                        : ROOT.kOrange + 2,
    "QCD"                               : ROOT.kYellow + 2,
    "q_{top} = 4/3"                     : ROOT.kViolet + 8
})

# Can be used to rename all sorts of items, like bin-names, axis-titles, etc.
s.pretty_names.update({
    "photonInputDummy"              : "preselected",
    "largeEtFilter"                 : "large e_{T}",
    "cocFilter"                     : "#DeltaR(photon, jet/#mu)",
    "tightIDFilter"                 : "tight photon ID",
    "PhotonFilteta"                 : "#eta",
    "PhotonFiltjurassicecaliso"     : "ecal iso",
    "PhotonFilthaspixelseeds"       : "pixelseed",
    "PhotonFilthcaliso"             : "hcal iso",
    "PhotonFiltetcut"               : "E_{T}",
    "PhotonFiltsigmaietaieta"       : "#sigma_{i #eta i #eta}",
    "PhotonFilthollowconetrackiso"  : "track iso",
    "PhotonFiltetawidth"            : "#eta witdh",
    "PhotonFilthadronicoverem"      : "H/E",
    "PhotonFiltdrjet"               : "#DeltaR(photon, jet)",
    "PhotonFiltdrmuon"              : "#DeltaR(photon, #mu)",
    "PhotonFiltptrelDrjet"          : "p_{T,photon} / p_{T,jet}"
})
