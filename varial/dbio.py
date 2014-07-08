import cPickle
import sqlite3
from ROOT import TObject
from ast import literal_eval

import analysis
import settings
import wrappers


_db_conn = None


def _init(db_name=None):
    global _db_conn
    if _db_conn:
        _close()
    name = db_name or settings.varial_working_dir + settings.db_name
    _db_conn = sqlite3.connect(name)
    _db_conn.isolation_level = None
    c = _db_conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS '
              'dot_info (path VARCHAR UNIQUE, data)')
    c.execute('CREATE TABLE IF NOT EXISTS '
              'dot_root (path VARCHAR, key VARCHAR, data)')


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
    path = analysis.cwd + (name or wrp.name)
    c = _db_conn.cursor()
    c.execute('DELETE FROM dot_info WHERE path=?', (path,))
    c.execute('DELETE FROM dot_root WHERE path=?', (path,))

    # write root objs
    if any(isinstance(o, TObject) for o in wrp.__dict__.itervalues()):
        wrp.root_file_obj_names = {}
        for key, value in wrp.__dict__.iteritems():
            if not isinstance(value, TObject):
                continue
            c.execute(
                'INSERT INTO dot_root VALUES (?,?,?)',
                (path, key, cPickle.dumps(value))
            )
            wrp.root_file_obj_names[key] = value.GetName()

    # write wrp
    c.execute(
        'INSERT INTO dot_info VALUES (?,?)',
        (path, wrp.pretty_writeable_lines())
    )


def read(name):
    if not _db_conn:
        _init()
    path = analysis.cwd + name
    c = _db_conn.cursor()
    c.execute('SELECT data FROM dot_info WHERE path=?', (path,))
    info = c.fetchone()
    if not info:
        raise RuntimeError('Data not found in db: %s' % path)
    info = literal_eval(info)
    if "root_file_obj_names" in info:
        for key, value in info["root_file_obj_names"].iteritems():
            c.execute(
                'SELECT data FROM dot_info WHERE path=? AND key=?',
                (path, key)
            )
            obj = c.fetchone()
            if not obj:
                raise RuntimeError('Data not found in db: %s, %s' % (path, key))
            obj = cPickle.loads(str(obj[0]))
            info[key] = obj
        del info["root_file_obj_names"]
    klass = getattr(wrappers, info.get("klass"))
    wrp = klass(**info)
    return wrp


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
