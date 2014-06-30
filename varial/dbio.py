import cPickle
import sqlite3

import analysis


_db_conn = None


def _init(db_name='varial.db'):
    global _db_conn
    if _db_conn:
        _close()
    _db_conn = sqlite3.connect(db_name)
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
def write(wrp):
    if not _db_conn:
        _init()
    with _db_conn:
        path = analysis.cwd + wrp.name
        c = _db_conn.cursor()
        c.execute('DELETE FROM analysis WHERE path=?', path)
        c.execute(
            'INSERT INTO analysis VALUES (?,?)',
            (path, cPickle.dumps(wrp))
        )


def read(name):
    if not _db_conn:
        _init()
    with _db_conn:
        c = _db_conn.cursor()
        c.execute('SELECT data FROM analysis WHERE path=?', (name,))
        return cPickle.loads(c.fetchone()[0])


def get(name):
    return read(name)


########################################################## i/o with aliases ###
def generate_aliases(path=None):
    pass


def load_histogram(alias):
    pass


################################################### write and close on exit ###
import atexit
atexit.register(_close)
