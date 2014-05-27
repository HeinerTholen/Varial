import atexit
import glob
from os.path import abspath, basename, dirname, exists, join
from ast import literal_eval
from itertools import takewhile
from ROOT import TFile, TDirectory, TH1, TObject

import monitor
import sample
import wrappers



class NoDictInFileError(Exception): pass
class NoObjectError(Exception): pass
class NoHistogramError(Exception): pass


############################################################ root file refs ###
_open_root_files = {}


def get_open_root_file(filename):
    if filename in _open_root_files:
        file_handle = _open_root_files[filename]
    else:
        if len(_open_root_files) > 998:
            monitor.message(
                "diskio",
                "WARNING to many open root files. Closing all. "
                "Please check for lost histograms. "
                "(Use hist.SetDirectory(0) to keep them)"
            )
            close_open_root_files()
        file_handle = TFile.Open(filename, "READ")
        _open_root_files[filename] = file_handle
    return file_handle


def close_open_root_files():
    for name, file_handle in _open_root_files.iteritems():
        file_handle.Close()
    _open_root_files.clear()


##################################################### read / write wrappers ###
def write(wrp, filename=None):
    """Writes wrapper to disk, including root objects."""
    if not filename:
        filename = join(analysis.cwd, wrp.name)
    if filename[-5:] == ".info":
        filename = filename[:-5]
    # write root objects (if any)
    if any(isinstance(o, TObject) for o in wrp.__dict__.itervalues()):
        wrp.root_filename = basename(filename+".root")
        f = TFile.Open(filename+".root", "RECREATE")  # TODO check for validity
        f.cd()
        _write_wrapper_objs(wrp, f)
        f.Close()
    # write wrapper infos
    with open(filename+".info", "w") as f:
        _write_wrapper_info(wrp, f)
    _clean_wrapper(wrp)


def _write_wrapper_info(wrp, file_handle):
    """Serializes Wrapper to python code dict."""
    history, wrp.history = wrp.history, str(wrp.history)
    file_handle.write(wrp.pretty_writeable_lines() + " \n\n")
    file_handle.write(wrp.history + "\n")
    wrp.history = history


def _write_wrapper_objs(wrp, file_handle):
    """Writes root objects on wrapper to disk."""
    wrp.root_file_obj_names = {}
    for key, value in wrp.__dict__.iteritems():
        if not isinstance(value, TObject):
            continue
        dirfile = file_handle.mkdir(key, key)
        dirfile.cd()
        value.Write()
        dirfile.Close()
        wrp.root_file_obj_names[key] = value.GetName()


def read(filename):
    """Reads wrapper from disk, including root objects."""
    if filename[-5:] != ".info":
        filename += ".info"
    filename = join(analysis.cwd, filename)
    with open(filename, "r") as f:
        info = _read_wrapper_info(f)
    if "root_filename" in info:
        _read_wrapper_objs(info, dirname(filename))
    klass = getattr(wrappers, info.get("klass"))
    wrp = klass(**info)
    _clean_wrapper(wrp)
    return wrp


def _read_wrapper_info(file_handle):
    """Instaciates Wrapper from info file, without root objects."""
    lines = takewhile(lambda l: l!="\n", file_handle)
    lines = (l.strip() for l in lines)
    lines = "".join(lines)
    info = literal_eval(lines)
    if not type(info) == dict:
        raise NoDictInFileError("Could not read file: "+file_handle.name)
    return info


def _read_wrapper_objs(info, path):
    root_file = join(path, info["root_filename"])
    obj_paths = info["root_file_obj_names"]
    for key, value in obj_paths.iteritems():
        obj = _get_obj_from_file(root_file, [key, value])
        if hasattr(obj, "SetDirectory"):
            obj.SetDirectory(0)
        info[key] = obj


def _clean_wrapper(wrp):
    del_attrs = ["root_filename", "root_file_obj_names", "wrapped_object_key"]
    for attr in del_attrs:
        if hasattr(wrp, attr):
            delattr(wrp, attr)


def get(filename, default=None):
    """Reads wrapper from disk if availible, else returns default."""
    if exists(join(analysis.cwd, '%s.info' % filename)):
        return read(filename)
    else:
        return default


def remove(filename):
    """Deletes wrapper files if availible."""
    path = join(analysis.cwd, filename)
    if exists(path + '.info'):
        os.remove(path + '.info')
    if exists(path + '.root'):
        os.remove(path + '.root')


########################################################## i/o with aliases ###
def generate_fs_aliases(root_file_path, sample_inst):
    """Produces list of all fileservice histograms for registered samples."""
    fs_file = get_open_root_file(root_file_path)
    assert isinstance(sample_inst, sample.Sample)  # TODO: exception
    for analyzer_key in fs_file.GetListOfKeys():
        analyzer = analyzer_key.ReadObj()
        analyzer_name = analyzer_key.GetName()
        for histo_key in analyzer.GetListOfKeys():
            histo_name = histo_key.GetName()
            yield wrappers.FileServiceAlias(
                histo_name,
                analyzer_name,
                sample_inst
            )


def generate_aliases(glob_path="./*.root"):
    """Looks only for *.root files and produces aliases."""
    for filename in glob.iglob(glob_path):
        root_file = get_open_root_file(filename)
        for alias in _recursive_make_alias(
            root_file,
            abspath(filename),
            []
        ):
            yield alias


def _recursive_make_alias(root_dir, filename, in_file_path):
    for key in root_dir.GetListOfKeys():
        in_file_path += [key.GetName()]
        if key.IsFolder():
            for alias in _recursive_make_alias(
                key.ReadObj(),
                filename,
                in_file_path
            ):
                yield alias
        else:
            yield wrappers.Alias(
                filename,
                in_file_path[:]
            )
        in_file_path.pop(-1)


def load_histogram(alias):
    """
    Returns a wrapper with a fileservice histogram.
    """
    histo = _get_obj_from_file(
        alias.file_path,
        alias.in_file_path
    )
    if not isinstance(histo, TH1):
        raise NoHistogramError(
            "Loaded object is not of type TH1: %s" % str(histo)
        )
    histo.Sumw2()
    wrp = wrappers.HistoWrapper(histo, **alias.all_info())
    if isinstance(alias, wrappers.FileServiceAlias):
        histo.SetTitle(alias.legend)
        wrp.history = (
            "FileService(%s, %s, %s)" % (
                alias.sample, alias.analyzer, alias.name)
        )
    else:
        wrp.history = repr(alias)
    return wrp


def _get_obj_from_file(filename, in_file_path):
    obj = get_open_root_file(filename)
    # browse through file
    for name in in_file_path:
        obj_key = obj.GetKey(name)
        if not obj_key:
            raise NoObjectError(
                "I cannot find '%s' in root file '%s'!" % (name, filename))
        obj = obj_key.ReadObj()
    return obj


################################################### write and close on exit ###
import analysis


def write_fileservice():
    for wrp in analysis.fs_wrappers.itervalues():
        write(wrp)

atexit.register(write_fileservice)
atexit.register(close_open_root_files)
