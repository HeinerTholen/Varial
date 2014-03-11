
import os
import glob
from ast import literal_eval
from itertools import takewhile
import settings
import wrappers
import monitor
from ROOT import TFile, TDirectory, TH1, TObject


class NoDictInFileError(Exception): pass
class NoObjectError(Exception): pass
class NoHistogramError(Exception): pass


class IoRefPool(object):
    _open_root_files = {}
    aliases = []

    def get_root_file(self, filename):
        if filename in self._open_root_files:
            file_handle = io_ref_pool._open_root_files[filename]
        else:
            if len(self._open_root_files) > 998:
                monitor.message(
                    "diskio",
                    "WARNING to many open root files. Closing all. "
                    "Please check for lost histograms. (Use hist.SetDirectory(0) to keep them)"
                )
                self.close_files()
            file_handle = TFile.Open(filename, "READ")
            self._open_root_files[filename] = file_handle
        return file_handle

    def __del__(self):
        self.close_files()

    def close_files(self):
        for name, file_handle in self._open_root_files.iteritems():
            file_handle.Close()
        self._open_root_files.clear()
        del self.aliases[:]
io_ref_pool = IoRefPool()


def drop_io_refs():
    io_ref_pool.close_files()


def write(wrp, filename=None):
    """Writes wrapper to disk, including root objects."""
    if not filename:
        filename = os.path.join(settings.dir_result, wrp.name)
    if filename[-5:] == ".info":
        filename = filename[:-5]
    # write root objects (if any)
    if any(isinstance(o, TObject) for o in wrp.__dict__.itervalues()):
        wrp.root_filename = filename+".root"
        f = TFile.Open(wrp.root_filename, "RECREATE")
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
    wrp.root_file_obj_names  = {}
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
    if info.has_key("root_filename"):
        _read_wrapper_objs(info)
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


def _read_wrapper_objs(info):
    root_file = info["root_filename"]
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
    if io_ref_pool.aliases:
        return io_ref_pool.aliases
    fs_filenames = glob.glob(_get_fileservice_filename("*"))
    aliases = []
    for filename in fs_filenames:
        fs_file = io_ref_pool.get_root_file(filename)
        sample_name = os.path.basename(filename)[:-5]
        if not settings.samples.has_key(sample_name):
            continue
        is_data = settings.samples[sample_name].is_data
        legend = settings.samples[sample_name].legend
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
    io_ref_pool.aliases = aliases   #TODO this should be dict path->aliases
    return aliases


def generate_aliases(directory="./"):
    """Looks only for *.root files and produces aliases."""
    for filename in glob.iglob(os.path.join(directory, "*.root")):
        root_file = io_ref_pool.get_root_file(filename)
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
    wrp.lumi = settings.samples[alias.sample].lumi
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
    file = io_ref_pool.get_root_file(filename)
    obj = file
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
    return settings.DIR_FILESERVICE + sample + ".root"



