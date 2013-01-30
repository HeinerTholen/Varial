
import os.path
import glob
import settings
import singleton
import wrappers
from ROOT import TFile, TH1


class HistoDispatch(object):
    """
    Central dispatch for histograms
    """
    __metaclass__ = singleton.Singleton

    class NoObjectError(Exception): pass
    class NoHistogramError(Exception): pass

    def __init__(self):
        self.open_root_files = {}
        self.aliases = None

    def __del__(self):
        for name, file in self.open_root_files.iteritems():
            file.Close()
        del self.open_root_files

    def fileservice_aliases(self):
        """
        Produces list of all fileservice histograms for registered samples.
        """
        #TODO: Man, that could be prettier!
        if self.aliases:
            return self.aliases
        fs_filenames = glob.glob(self._get_fileservice_filename("*"))
        aliases = []
        for filename in fs_filenames:
            fs_file = self._get_root_file(filename)
            sample_name = os.path.basename(filename)[:-5]
            if not settings.samples.has_key(sample_name):
                continue
            is_data = settings.samples[sample_name].is_data
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
                            is_data
                        )
                    )
        self.aliases = aliases
        return aliases

    def load_histogram(self, alias):
        """
        Returns a wrapper with a fileservice histogram.
        """
        if isinstance(alias, wrappers.FileServiceAlias):
            histo = self._load_fileservice_histo(alias)
            histo.history = (
                "FileService(" +
                alias.sample + ", " +
                alias.analyzer + ", " +
                alias.name + ")"
            )
        else:
            histo = self._load_non_fileservice_histo(alias)
            histo.history = repr(alias)
        return histo

    def _load_fileservice_histo(self, alias):
        histo = self._get_obj_from_file(
            self._get_fileservice_filename(alias.sample),
            alias.in_file_path
        )
        if not isinstance(histo, TH1):
            raise self.NoHistogramError(
                "Loaded object is not of type TH1: ", str(object)
            )
        histo.Sumw2()
        histo.SetTitle(settings.samples[alias.sample].legend)
        wrp = wrappers.HistoWrapper(histo, **alias.all_info())
        wrp.lumi = settings.samples[alias.sample].lumi
        return wrp

    def _load_non_fileservice_histo(self, alias):
        histo = self._get_obj_from_file(
            alias.filename,
            alias.in_file_path
        )
        if not isinstance(histo, TH1):
            raise self.NoHistogramError(
                "Loaded object is not of type TH1: ", str(object)
            )
        info_filename = alias.filename[:-5] + ".info"
        if os.path.exists(info_filename):
            return wrappers.HistoWrapper.create_from_file(info_filename, histo)
        else:
            return wrappers.HistoWrapper(histo, **alias.all_info())

    def _get_obj_from_file(self, filename, in_file_path):
        file = self._get_root_file(filename)
        obj = file
        # browse through file
        for name in in_file_path:
            obj_key = obj.GetKey(name)
            if not obj_key:
                raise self.NoObjectError(
                    "I cannot find '"
                    + name
                    + "' in root file '"
                    + filename
                    + "'!"
                )
            obj = obj_key.ReadObj()
        return obj

    def _get_fileservice_filename(self, sample):
        return settings.DIR_FILESERVICE + sample + ".root"

    def _get_root_file(self, filename):
        if self.open_root_files.has_key(filename):
            file = self.open_root_files[filename]
        else:
            file = TFile.Open(filename, "READ")
            self.open_root_files[filename] = file
        return file


class HistoPool(object):
    """Storage for all kinds of Wrappers"""
    __metaclass__ = singleton.Singleton
    _pool = []

    def put(self, wrp):
        self._pool.append(wrp)

    def get(self):
        return (wrp for wrp in self._pool)

    def reset(self):
        del self._pool[:]