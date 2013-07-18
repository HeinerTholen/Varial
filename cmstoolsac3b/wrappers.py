# HistoOperations.py

import sys
import settings # only imported for ROOT-system startup
from ROOT import TH1, THStack, TCanvas
from ast import literal_eval

class _dict_base(object):
    """
    Overwrites __str__ to print classname and __dict__
    """
    class NoDictInFileError(Exception): pass

    def __str__(self):
        """
        Writes all __dict__ entries into a string.
        """
        name = self.__dict__.get("name", self.__class__.__name__)
        txt = "_____________" + name + "____________\n"
        txt += self.pretty_info_lines()
        txt += "\n"
        return txt

    def __repr__(self):
        return str(self)

    def all_info(self):
        """
        Returns copy of self.__dict__.
        """
        return dict(self.__dict__)

    def pretty_info_lines(self):
        keys = sorted(self.__dict__.keys())
        return "{\n" + ",\n".join(
            "%20s: "%k + repr(getattr(self, k)) for k in keys
        ) + ",\n}"


class Alias(_dict_base):
    """
    Alias of a histogram on disk.

    :param  filename:       path to root file
    :param  in_file_path:   path to ROOT-object within the root file.
    :type   in_file_path:   list of strings
    """
    def __init__(self, filename, in_file_path):
        self.filename = filename
        self.in_file_path = in_file_path


class FileServiceAlias(Alias):
    """
    Alias of a histogram in the fileservice output.

    :param  name:           histogram name
    :param  analyzer:       name of the CMSSW analyzer
    :param  sample:         name of the sample
    :param  is_data:        data or not?
    :type   is_data:        bool
    """
    def __init__(self, name, analyzer, sample, legend, is_data = False):
        super(FileServiceAlias, self).__init__(sample, [analyzer, name])
        self.name           = name
        self.analyzer       = analyzer
        self.sample         = sample
        self.legend         = legend
        self.is_data        = is_data


class Wrapper(_dict_base):
    """
    Wrapper base class.

    **Keywords:** ``name``, ``title`` and ``history`` are accepted.

    **Example:**

    >>> w = Wrapper(name="n", title="t", history="h")
    >>> info = w.all_info()
    >>> info["name"]
    'n'
    """
    class FalseObjectError(Exception):
        """Exception for false type."""

    def __init__(self, **kws):
        self.name           = kws.get("name", "")
        self.title          = kws.get("title", self.name)
        self.history        = kws.get("history", "")

    def write_info_file(self, info_filename):
        """
        Serializes Wrapper to python code dict.

        Class is encoded as 'klass',
        history (see :ref:`history-module`) is printed out nicely.

        :param  info_filename:  filename to store wrapper infos with suffix.
        """
        self.klass = self.__class__.__name__
        history, self.history = self.history, repr(str(self.history))
        with open(info_filename, "w") as file:
            file.write(repr(self.all_info()) + " \n")
            file.write(self.pretty_info_lines() + " \n\n")
            file.write(str(history))
        del self.klass
        self.history = history

    @classmethod
    def create_from_file(cls, info_filename, wrapped_obj = None):
        """
        Reads serialized dict and creates wrapper.

        :param  info_filename:  filename to read wrapper infos from.
        :param  wrapped_obj:    object to be wrapped by the newly instantiated wrapper.
        :type   wrapped_obj:    TH1/THStack/TCanvas/...
        :returns:               Wrapper type according to info file
        """
        with open(info_filename, "r") as file:
            line = file.readline()
            info = literal_eval(line)
        if not type(info) == dict:
            raise cls.NoDictInFileError(
                "Could not read file: " + info_filename
            )
        this_mod = sys.modules[__name__]
        klass = getattr(this_mod, info.get("klass"))
        del info["klass"]
        if wrapped_obj:
            wrp = klass(wrapped_obj, **info)
        elif klass == FloatWrapper:
            wrp = klass(info["float"], **info)
        else:
            wrp = klass(**info)
        for k, v in info.iteritems():
            setattr(wrp, k, v)
        return wrp

    def primary_object(self):
        """Overwrite! Should returned wrapped object."""


class FloatWrapper(Wrapper):
    """
    Wrapper for float values.

    **Keywords:** See superclass.

    :raises: self.FalseObjectError
    """
    def __init__(self, value, **kws):
        super(FloatWrapper, self).__init__(**kws)
        if not (type(value) == float or type(value) == int):
            raise self.FalseObjectError(
                "FloatWrapper needs a float or int as first argument"
            )
        self.float = float(value)


class HistoWrapper(Wrapper):
    """
    Wrapper class for a ROOT histogram TH1.
    
    **Keywords:**
    ``lumi``,
    ``is_data``,
    ``sample``,
    ``analyzer``,
    and also see superclass.

    :raises: self.FalseObjectError
    """
    def __init__(self, histo, **kws):
        if not isinstance(histo, TH1):
            raise self.FalseObjectError(
                "HistoWrapper needs a TH1 instance as first argument"
            )
        super(HistoWrapper, self).__init__(**kws)
        self.histo          = histo
        self.name           = histo.GetName()
        self.title          = histo.GetTitle()
        self.is_data        = kws.get("is_data", False)
        self.lumi           = kws.get("lumi", 1.)
        self.sample         = kws.get("sample", "")
        self.legend         = kws.get("legend", "")
        self.analyzer       = kws.get("analyzer", "")
        self.filename       = kws.get("filename", "")
        self.in_file_path   = kws.get("in_file_path", "")
        if not self.filename:
            self.filename       = self.sample + ".root"
            self.in_file_path   = [self.analyzer, self.name]

    def all_info(self):
        """
        :returns: dict with all members, but not the histo.
        """
        info = super(HistoWrapper, self).all_info()
        del info["histo"]
        return info

    def primary_object(self):
        return self.histo


class StackWrapper(HistoWrapper):
    """
    Wrapper class for a ROOT histogram stack THStack.

    **Keywords:** See superclass.

    :raises: self.FalseObjectError
    """
    def __init__(self, stack, **kws):
        if not isinstance(stack, THStack):
            raise self.FalseObjectError(
                "StackWrapper needs a THStack instance as first argument"
            )
        super(StackWrapper, self).__init__(
            self._add_stack_up(stack),
            **kws
        )
        self.stack          = stack
        self.name           = stack.GetName()
        self.title          = stack.GetTitle()

    def _add_stack_up(self, stack):
        sum_hist = None
        for histo in stack.GetHists():
            if sum_hist:
                sum_hist.Add(histo)
            else:
                sum_hist = histo.Clone()
        return sum_hist

    def all_info(self):
        """
        :returns: dict with all members, but not the stack.
        """
        info = super(StackWrapper, self).all_info()
        del info["stack"]
        return info

    def primary_object(self):
        return self.stack


class CanvasWrapper(Wrapper):
    """
    Wrapper class for a ROOT canvas TCanvas.

    **Keywords:** ``lumi`` and also see superclass.

    :raises: self.FalseObjectError
    """
    def __init__(self, canvas, **kws):
        if not isinstance(canvas, TCanvas):
            raise self.FalseObjectError(
                "CanvasWrapper needs a TCanvas instance as first argument!"
            )
        super(CanvasWrapper, self).__init__(**kws)
        self.canvas     = canvas
        self.main_pad   = kws.get("main_pad", canvas)
        self.second_pad = kws.get("second_pad")
        self.legend     = kws.get("legend")
        self.first_drawn= kws.get("first_drawn")
        self.x_bounds   = kws.get("x_bounds")
        self.y_bounds   = kws.get("y_bounds")
        self.y_min_gr_0 = kws.get("y_min_gr_0")
        self.lumi       = kws.get("lumi", 1.)
        self.name       = canvas.GetName()
        self.title      = canvas.GetTitle()

    def primary_object(self):
        self.canvas.Modified()
        self.canvas.Update()
        return self.canvas


if __name__ == "__main__":
    import doctest
    doctest.testmod()

