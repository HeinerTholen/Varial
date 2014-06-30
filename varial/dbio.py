import cPickle
import sqlite3

import analysis
import settings


_db_conn = None


def _init(db_name=None):
    global _db_conn
    if _db_conn:
        _close()
    name = db_name or settings.varial_working_dir + settings.db_name
    _db_conn = sqlite3.connect(name)
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
    if not _db_conn:
        _init()
    with _db_conn:
        path = analysis.cwd + (name or wrp.name)
        c = _db_conn.cursor()
        c.execute('DELETE FROM analysis WHERE path=?', (path,))
        c.execute(
            'INSERT INTO analysis VALUES (?,?)',
            (path, cPickle.dumps(wrp))
        )


def read(name):
    if not _db_conn:
        _init()
    with _db_conn:
        path = analysis.cwd + name
        c = _db_conn.cursor()
        c.execute('SELECT data FROM analysis WHERE path=?', (path,))
        data = c.fetchone()
        if data:
            return cPickle.loads(str(data[0]))
        else:
            raise RuntimeError('Data not found in db: %s' % path)


def get(name):
    try:
        return read(name)
    except RuntimeError:
        return None


########################################################## i/o with aliases ###
def generate_aliases(path=None):
    pass


def load_histogram(alias):
    pass


################################################### write and close on exit ###
import atexit
atexit.register(_close)
