import diskio
import generators
import operations
import rendering
import settings
import wrappers


def use_fancy_folders():
    s = settings
    s.DIR_FILESERVICE = "outputFileService/"
    s.DIR_LOGS        = "outputLogs/"
    s.DIR_CONFS       = "outputConfs/"
    s.DIR_PLOTS       = "outputPlots/"
    s.dir_result      = s.DIR_PLOTS
    s.dir_pstprc      = s.DIR_PSTPRCINFO
    s.stack_dir_result = [s.DIR_PLOTS]
    s.stack_dir_pstprc = [s.DIR_PSTPRCINFO]


def use_root_batch():
    import ROOT
    ROOT.gROOT.SetBatch()