import os.path
import glob
import settings
import collections
import itertools
import wrappers
import inspect

class Sample(wrappers._dict_base):
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
        if not getattr(self, "name", 0):
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
        if type(self.input_files) == str:
            self.input_files = [self.input_files]
        if not type(self.cfg_builtin) == dict:
            raise self.MissingDefinition("cfg_builtin must be of type dict")
        if not self.legend:
            self.legend = self.name


def _check_n_load(field):
    if inspect.isclass(field) and issubclass(field, Sample):
        smp = field()
        if hasattr(smp, "enable"):
            if smp.enable:
                return {smp.name: smp}
        elif settings.default_enable_sample:
            return {smp.name: smp}
    return {}

def load_samples(module):
    """
    Get sample instances from a module.

    :param module: modules to import samples from
    :type  module: module
    :returns:      dict of sample classes
    """
    samples = {}
    if isinstance(module, collections.Iterable):
        for mod in module:
            samples.update(load_samples(mod))
    else:
        for name in dir(module):
            if name[0] == "_": continue
            field = getattr(module, name)
            try: # handle iterable
                for f in field: samples.update(_check_n_load(f))
            except TypeError: # not an iterable
                samples.update(_check_n_load(field))
    return samples

def generate_samples(in_filenames, in_path="", out_path=""):
    """
    Generates samples and adds them to settings.samples.

    The input filename without suffix will be taken as sample name.

    :param in_filenames:    names of inputfiles
    :param in_path:         input path
    :param out_path:        output path
    :returns:               dict of sample classes
    """
    if type(in_filenames) is str:
        in_filenames = [in_filenames]
    samples = {}
    for fname in in_filenames:
        basename    = os.path.basename(fname)
        samplename  = os.path.splitext(basename)[0]
        class sample_subclass(Sample):
            name = samplename
            lumi = 1.
            input_files = in_path + fname
            output_file = out_path
        samples[samplename] = sample_subclass
    return samples

def generate_samples_glob(glob_path, out_path):
    """Globs for files and creates according samples."""
    in_filenames = glob.glob(glob_path)
    in_filenames = itertools.imap(
        lambda t: "file:" + t, # prefix with 'file:' for cmssw
        in_filenames
    )
    return generate_samples(
        in_filenames, 
        "", 
        out_path
    )

