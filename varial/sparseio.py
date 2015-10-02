"""
Read/Write wrappers on disk. Directory based.

This io module is specialized for faster writing to disk while plotting. Instead
of producing individual .info and .root files for every plot, the info and root
content accumulated in single files and written at once.

Only generator modules are provided.
"""


from ROOT import TFile
import cPickle
import os

import analysis
import monitor


_rootfile = 'varial_sparseio.root'
_infofile = 'varial_sparseio.info'
use_analysis_cwd = True


def bulk_read_info_dict(dir_path=None):
    """Returns dict of info-dicts (not wrapper instances)"""
    if use_analysis_cwd:
        dir_path = os.path.join(analysis.cwd, dir_path)
    infofile = os.path.join(dir_path, _infofile)
    if not os.path.exists(infofile):
        return {}

    with open(infofile) as f:
        res = cPickle.load(f)
    assert(type(res) == dict)
    return res


def bulk_write(wrps, dir_path, name_func, suffices=None):
    """Writes wrps en block."""
    # prepare
    if use_analysis_cwd:
        dir_path = os.path.join(analysis.cwd, dir_path)
    infofile = os.path.join(dir_path, _infofile)
    rootfile = os.path.join(dir_path, _rootfile)
    wrps_dict = dict()
    for w in wrps:
        name = name_func(w)
        if name in wrps_dict:
            monitor.message(
                'sparseio',
                'WARNING Overwriting name from this session: %s in path: %s' %
                (name, dir_path)
            )
        wrps_dict[name] = w
    info = dict((name, w.all_writeable_info())
                for name, w in wrps_dict.iteritems())

    # write out
    with open(infofile, 'w') as f_info:
        cPickle.dump(info, f_info)
    f_root = TFile.Open(rootfile, 'RECREATE')
    f_root.cd()
    for name, w in wrps_dict.iteritems():
        dirfile = f_root.mkdir(name, name)
        dirfile.cd()
        w.obj.Write()
        dirfile.Close()
    f_root.Close()
    for suffix in suffices:
        for name, w in wrps_dict.iteritems():
            w.obj.SaveAs(os.path.join(dir_path, name) + suffix)

    return wrps