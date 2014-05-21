import atexit
import os
import glob
from ast import literal_eval
from itertools import takewhile
from ROOT import TFile, TDirectory, TH1, TObject

import analysis
import wrappers
import monitor



class NoDictInFileError(Exception): pass
class NoObjectError(Exception): pass
class NoHistogramError(Exception): pass


############################################################# root file refs ###
_open_root_files = {}
_aliases = []


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
    del _aliases[:]


############################################################### file service ###
_file_service = {}


def fileservice(filename="fileservice", autosave=True):
    """Return FileService Wrapper for automatic storage."""
    if autosave:
        if not filename in _file_service:
            _file_service[filename] = wrappers.Wrapper(name=filename)
        return _file_service[filename]
    else:
        return wrappers.Wrapper(name=filename)


def write_fileservice():
    for wrp in _file_service.itervalues():
        write(wrp)


############################################################### read / write ###
def write(wrp, filename=None):
    """Writes wrapper to disk, including root objects."""
    if not filename:
        filename = os.path.join(analysis.cwd, wrp.name)
    if filename[-5:] == ".info":
        filename = filename[:-5]
    # write root objects (if any)
    if any(isinstance(o, TObject) for o in wrp.__dict__.itervalues()):
        wrp.root_filename = os.path.basename(filename+".root")
        f = TFile.Open(filename+".root", "RECREATE")   #TODO check for validity
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
    f = open(filename, "r")
    info = _read_wrapper_info(f)
    f.close()
    if "root_filename" in info:
        _read_wrapper_objs(info, os.path.dirname(filename))
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
    root_file = os.path.join(path, info["root_filename"])
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


def fileservice_aliases():
    """Produces list of all fileservice histograms for registered samples."""
    if len(_aliases):
        return _aliases[:]
    fs_filenames = glob.glob(_get_fileservice_filename("*"))
    aliases = []
    for filename in fs_filenames:
        fs_file = get_open_root_file(filename)
        sample_name = os.path.basename(filename)[:-5]
        if sample_name not in analysis.all_samples:
            continue
        is_data = analysis.all_samples[sample_name].is_data
        legend = analysis.all_samples[sample_name].legend
        for analyzer_key in fs_file.GetListOfKeys():
            analyzer = analyzer_key.ReadObj()
            analyzer_name = analyzer_key.GetName()
            for histo_key in analyzer.GetListOfKeys():
                histo_name = histo_key.GetName()
                aliases.append(
                    wrappers.FileServiceAlias(
                        histo_name,
                        analyzer_name,
                        sample_name,
                        legend,
                        is_data
                    )
                )
    _aliases[:] = aliases  # TODO this should be dict path->aliases
    return aliases


def generate_aliases(directory="./"):
    """Looks only for *.root files and produces aliases."""
    for filename in glob.iglob(os.path.join(directory, "*.root")):
        root_file = get_open_root_file(filename)
        for alias in _recursive_make_alias(
            root_file,
            os.path.abspath(filename),
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
    if isinstance(alias, wrappers.FileServiceAlias):
        histo = _load_fileservice_histo(alias)
        histo.history = (
            "FileService(" +
            alias.sample + ", " +
            alias.analyzer + ", " +
            alias.name + ")"
        )
    else:
        histo = _load_non_fileservice_histo(alias)
        histo.history = repr(alias)
    return histo


def _load_fileservice_histo(alias):
    histo = _get_obj_from_file(
        _get_fileservice_filename(alias.sample),
        alias.in_file_path
    )
    if not isinstance(histo, TH1):
        raise NoHistogramError(
            "Loaded object is not of type TH1: ", str(object)
        )
    histo.Sumw2()
    histo.SetTitle(alias.legend)
    wrp = wrappers.HistoWrapper(histo, **alias.all_info())
    wrp.lumi = analysis.all_samples[alias.sample].lumi
    return wrp


def _load_non_fileservice_histo(alias):
    histo = _get_obj_from_file(
        alias.filename,
        alias.in_file_path
    )
    if not isinstance(histo, TH1):
        raise NoHistogramError(
            "Loaded object is not of type TH1: ", str(object)
        )
    return wrappers.HistoWrapper(histo, **alias.all_info())


def _get_obj_from_file(filename, in_file_path):
    obj = get_open_root_file(filename)
    # browse through file
    for name in in_file_path:
        obj_key = obj.GetKey(name)
        if not obj_key:
            raise NoObjectError(
                "I cannot find '"
                + name
                + "' in root file '"
                + filename
                + "'!"
            )
        obj = obj_key.ReadObj()
    return obj


def _get_fileservice_filename(sample):
    return analysis.cwd + sample + ".root"   # FIXME


#################################################### write and close on exit ###
atexit.register(write_fileservice)
atexit.register(close_open_root_files)