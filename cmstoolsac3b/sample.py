import os.path
import settings
import collections

class Sample(object):
    """
    Collect information about a sample. Subclass!

    Samples have to be declared by subclassing.
    **Example:** ::

        class SomeSample(Sample):
            input_files = [common_input_path + "data/dir/*.root"]
            lumi        = 4700.
            output_file = common_output_path
            legend      = "Data"

    For a full example of all features see :ref:`sample-definition-example`.
    """
    is_data         = False
    x_sec           = 0.
    n_events        = 0
    lumi            = 0.
    legend          = ""
    input_files     = []
    output_file     = ""
    cfg_builtin     = {}
    cfg_add_lines   = []
    class MissingDefinition(Exception): pass

    def __init__(self):
        # check/correct input
        if not self.name:
            self.name = self.__class__.__name__
        tbd = "TO BE DECLARED: "
        if not isinstance(self.input_files, collections.Iterable):
            self.input_files = [self.input_files]
        if not isinstance(self.cfg_add_lines, collections.Iterable):
            self.cfg_add_lines = [self.cfg_add_lines]
        if self.x_sec and self.n_events:
            self.lumi = self.n_events / float(self.x_sec)
        if not self.lumi:
            raise self.MissingDefinition(tbd + "lumi or (x_sec and n_events)")
        if not self.input_files:
            raise self.MissingDefinition(tbd + "input_files")
        if not type(self.cfg_builtin) == dict:
            raise self.MissingDefinition("cfg_builtin must be of type dict")
        if not self.legend:
            self.legend = self.name


def _check_n_load(field):
    if issubclass(field, Sample):
        smp = field()
        if smp.__dict__.get("enable", settings.default_enable_sample):
            settings.samples[smp.name] = smp


def load_samples(modules):
    """
    Adds samples to samples list in settings.

    :param modules: modules to import samples from
    :type  modules: module or module iterable
    :returns:       number of loaded samples
    """
    old_len = len(settings.samples)
    if not isinstance(modules, collections.Iterable):
        modules = [modules]
    for module in modules:
        for name in dir(module):
            if name[0] == "_": continue
            field = getattr(module, name)
            try:                                # handle iterables
                for f in field: _check_n_load(f)
            except TypeError:
                _check_n_load(field)
    return len(settings.samples) - old_len


def generate_samples(in_filenames, in_path="", out_path=""):
    """
    Generates samples and adds them to settings.samples.

    The input filename without suffix will be taken as sample name.

    :param in_filenames:    names of inputfiles
    :param in_path:         input path
    :param out_path:        output path
    :returns:               list of sample classes
    """
    if type(in_filenames) is str:
        in_filenames = [in_filenames]
    samples = []
    for fname in in_filenames:
        basename    = os.path.basename(fname)
        samplename  = os.path.splitext(basename)[0]
        class sample_subclass(Sample):
            name = samplename
            lumi = 1.
            input_files = in_path + fname
            output_file = out_path
        samples.append(sample_subclass)
    return samples