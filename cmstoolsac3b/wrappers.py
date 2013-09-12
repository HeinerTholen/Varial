
from ROOT import TH1, THStack, TCanvas, TObject

class _dict_base(object):
    """
    Overwrites __str__ to print classname and __dict__
    """
    def __str__(self):
        """Writes all __dict__ entries into a string."""
        name = self.__dict__.get("name", self.__class__.__name__)
        txt = "_____________" + name + "____________\n"
        txt += self.pretty_info_lines()
        txt += "\n"
        return txt

    def __repr__(self):
        return str(self)

    def all_info(self):
        """Returns copy of self.__dict__."""
        return dict(self.__dict__)

    def all_writeable_info(self):
        """Like all_info, but removes root objects."""
        return dict(
            (k,v)
            for k,v in self.__dict__.iteritems()
            if not isinstance(v, TObject)
        )

    def pretty_info_lines(self):
        return self._pretty_lines(sorted(self.__dict__.keys()))

    def pretty_writeable_lines(self):
        return self._pretty_lines(sorted(self.all_writeable_info().keys()))

    def _pretty_lines(self, keys):
        size = max(len(k) for k in keys) + 2
        return "{\n" + ",\n".join(
                    ("%"+str(size)+"s: ")%("'"+k+"'")
                    + repr(getattr(self, k))
                    for k in keys
                ) + ",\n}"

class Alias(_dict_base):
    """
    Alias of a histogram on disk.

    :param  filename:       path to root file
    :param  in_file_path:   path to ROOT-object within the root file.
    :type   in_file_path:   list of strings
    """
    def __init__(self, filename, in_file_path):
        self.klass          = self.__class__.__name__
        self.filename       = filename
        self.in_file_path   = in_file_path


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
    def __init__(self, **kws):
        self.name           = ""
        self.title          = self.name
        self.history        = ""
        self.__dict__.update(kws)
        self.klass          = self.__class__.__name__

    def _check_object_type(self, obj, typ):
        if not isinstance(obj, typ):
            raise TypeError(
                self.__class__.__name__
                + " needs a "
                + str(typ)
                + " instance as first argument! He got "
                + str(obj)
                + "."
            )

    def primary_object(self):
        """Overwrite! Should returned wrapped object."""

    def write_info_file(self, info_filename):
        """Functionality moved to package diskio."""
        raise Exception("Don't use this method! Use write() in module diskio.")

    def write_root_file(self, root_filename):
        """Functionality moved to package diskio."""
        raise Exception("Don't use this method! Use write() in module diskio.")

    @classmethod
    def create_from_file(cls, info_filename, wrapped_obj = None):
        """Functionality moved to package diskio."""
        raise Exception("Don't use this method! Use read() in module diskio.")

    def read_root_objs_from_file(self):
        """Functionality moved to package diskio."""
        raise Exception("Don't use this method! Use read() in module diskio.")


class FloatWrapper(Wrapper):
    """
    Wrapper for float values.

    **Keywords:** See superclass.

    :raises: TypeError
    """
    float_type = float
    def __init__(self, float, **kws):
        self._check_object_type(float, self.float_type)
        super(FloatWrapper, self).__init__(**kws)
        self.float = float


class HistoWrapper(Wrapper):
    """
    Wrapper class for a ROOT histogram TH1.
    
    **Keywords:**
    ``lumi``,
    ``is_data``,
    ``sample``,
    ``analyzer``,
    and also see superclass.

    :raises: TypeError
    """
    def __init__(self, histo, **kws):
        self._check_object_type(histo, TH1)
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

    :raises: TypeError
    """
    def __init__(self, stack, **kws):
        self._check_object_type(stack, THStack)
        if not kws.has_key("histo"):
            kws["histo"] = self._add_stack_up(stack)
        super(StackWrapper, self).__init__(**kws)
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

    :raises: TypeError
    """
    def __init__(self, canvas, **kws):
        self._check_object_type(canvas, TCanvas)
        super(CanvasWrapper, self).__init__(**kws)
        self.canvas     = canvas
        self.name       = canvas.GetName()
        self.title      = canvas.GetTitle()
        self.main_pad   = kws.get("main_pad", canvas)
        self.second_pad = kws.get("second_pad")
        self.legend     = kws.get("legend")
        self.first_drawn= kws.get("first_drawn")
        self.x_bounds   = kws.get("x_bounds")
        self.y_bounds   = kws.get("y_bounds")
        self.y_min_gr_0 = kws.get("y_min_gr_0")
        self.lumi       = kws.get("lumi", 1.)

    def primary_object(self):
        self.canvas.Modified()
        self.canvas.Update()
        return self.canvas


if __name__ == "__main__":
    import doctest
    doctest.testmod()

