"""
Store wrappers into a sqlite database.

Please checkout the :ref:`diskio-module` documentation for more information.
"""

import cPickle
import sqlite3

import analysis
import settings


_db_conn = None


def _init(db_name=None):
    global _db_conn
    if _db_conn:
        _close()
    if not db_name:
        if analysis.results_base:
            db_name = analysis.results_base.path + settings.db_name
        else:
            db_name = settings.varial_working_dir + settings.db_name
    _db_conn = sqlite3.connect(db_name, isolation_level='Exclusive')
    _db_conn.isolation_level = None
    c = _db_conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS analysis (path VARCHAR UNIQUE, data)')


def _close():
    global _db_conn
    if not _db_conn:
        return
    _db_conn.commit()
    _db_conn.close()
    _db_conn = None
    pass


##################################################### read / write wrappers ###
def write(wrp, name=None):
    """Write a wrapper."""
    if not _db_conn:
        _init()
    path = analysis.cwd + (name or wrp.name)
    c = _db_conn.cursor()
    c.execute('PRAGMA synchronous = 0')
    c.execute('PRAGMA journal_mode = OFF')
    c.execute('DELETE FROM analysis WHERE path=?', (path,))
    c.execute(
        'INSERT INTO analysis VALUES (?,?)',
        (path, cPickle.dumps(wrp))
    )
    _db_conn.commit()


def read(name):
    """Read a wrapper."""
    if not _db_conn:
        _init()
    path = analysis.cwd + name
    c = _db_conn.cursor()
    c.execute('SELECT data FROM analysis WHERE path=?', (path,))
    data = c.fetchone()
    if data:
        return cPickle.loads(str(data[0]))
    else:
        raise RuntimeError('Data not found in db: %s' % path)


def get(name, default=None):
    """Reads wrapper if availible, else returns default."""
    try:
        return read(name)
    except RuntimeError:
        return default


################################################### write and close on exit ###
import atexit
atexit.register(_close)
