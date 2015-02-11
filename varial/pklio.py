"""
Store wrappers into a pkl object for every directory.

Please checkout the :ref:`diskio-module` documentation for more information.
"""

import cPickle
import os

import analysis


_current_path = ''
_current_pack = {}
_changed = False


def _write_out():
    global _current_path, _current_pack, _changed

    if not _changed:
        return

    with open(os.path.join(_current_path, 'data.pkl'), 'w') as f:
        cPickle.dump(_current_pack, f)

    _changed = False


def _sync():
    global _current_path, _current_pack, _changed
    if analysis.cwd == _current_path:
        return

    # write out and load if possible
    _write_out()
    _current_path = analysis.cwd
    data_path = os.path.join(_current_path, 'data.pkl')
    if not os.path.exists(data_path):
        _current_pack = {}
    else:
        with open(data_path) as f:
            _current_pack = cPickle.load(f)
            assert(type(_current_pack) == dict)


##################################################### read / write wrappers ###
def write(wrp, name=None):
    """Write a wrapper."""
    global _current_pack, _changed
    _sync()
    _changed = True
    _current_pack[name or wrp.name] = wrp


def read(name):
    """Read a wrapper."""
    _sync()
    wrp = _current_pack.get(name)
    if wrp:
        return wrp
    else:
        raise RuntimeError('Data not found in: %s' % _current_path)


def get(name, default=None):
    """Reads wrapper if availible, else returns default."""
    try:
        return read(name)
    except RuntimeError:
        return default


################################################### write and close on exit ###
import atexit
atexit.register(_write_out)
