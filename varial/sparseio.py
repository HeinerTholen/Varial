"""
Read/Write wrappers on disk. Directory based.

This io module is specialized for faster writing to disk while plotting. Instead
of producing individual .info and .root files for every plot, the info and root
content accumulated in single files and written at once.

Only generator modules are provided.
"""


from ROOT import TFile, TDirectory, TH1, TObject, TTree
from os.path import basename, dirname, join
from itertools import takewhile
from ast import literal_eval
import resource
import glob
import os

import pklio


import history
import monitor
import sample
import settings
import wrappers


_rootfile = 'sparseio.root'
_infofile = 'sparseio.info'


def bulk_read_info_dict(dir_path):
    return {}


def bulk_write(wrps, dir_path, filename_func, suffices=None):
    return wrps