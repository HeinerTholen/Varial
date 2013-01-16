"""
Settings example for processing.

These are the default settings of the utilities.settings module, so this file
is really only for demonstrative purposes.
"""

import cmstoolsac3b.settings as s

def dummy_func():
    """This is just a dummy to include this source file."""

import multiprocessing
s.max_num_processes       = multiprocessing.cpu_count()
s.suppress_cmsRun_exec    = False
s.try_reuse_results       = False
s.default_enable_sample   = True
s.cfg_main_import_path       = ""
s.cfg_use_file_service    = True
s.cfg_output_module_name  = "out"
s.cfg_common_builtins     = {}

s.DIR_JOBINFO     = ".jobInfo/"
s.DIR_FILESERVICE = "outputFileService/"
s.DIR_LOGS        = "outputLogs/"
s.DIR_CONFS       = "outputConfs/"