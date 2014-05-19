######################################################### folder management ###
import os
import sys

DIR_JOBINFO     = ".jobInfo/"
DIR_PSTPRCINFO  = ".psrPrcInfo/"
DIR_FILESERVICE = "./"   #TODO: eliminate with process -> tool!!
DIR_LOGS        = "./"
DIR_CONFS       = "./"
DIR_PLOTS       = "./"  #TODO: outputResult!!

dir_result      = DIR_PLOTS
dir_pstprc      = DIR_PSTPRCINFO

stack_dir_result = [DIR_PLOTS]
stack_dir_pstprc = [DIR_PSTPRCINFO]

def push_tool_dir(name):
    stack_dir_result.append(name)
    stack_dir_pstprc.append(name)
    _set_dir_vars()

def pop_tool_dir():
    stack_dir_result.pop()
    stack_dir_pstprc.pop()
    _set_dir_vars()

def create_folder(path):
    if not os.path.exists(path):
        os.mkdir(path)

def create_folders():
    """
    Create all "DIR" prefixed folders.

    Looks up all string members starting with DIR (e.g. DIR_LOGS) and
    produces folders in the working dir according to the string.
    """
    this_mod = sys.modules[__name__]
    for name in dir(this_mod):
        if name[0:3] == "DIR":
            path = getattr(this_mod, name)
            create_folder(path)

def _set_dir_vars():
    this_mod = sys.modules[__name__]
    this_mod.dir_result = "/".join(stack_dir_result) + "/"
    this_mod.dir_pstprc = "/".join(stack_dir_pstprc) + "/"


