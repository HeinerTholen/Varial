import diskio
import generators
import operations
import rendering
import analysis
import wrappers


def use_fancy_folders():
    a = analysis
    a.DIR_WORKING = "varial/"
    a.cwd = a.DIR_WORKING
    a.stack_dir_result = [a.cwd]


def use_root_batch():
    import ROOT
    ROOT.gROOT.SetBatch()