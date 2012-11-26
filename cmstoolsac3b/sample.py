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
            obj = getattr(module, name)
            if issubclass(name, Sample):
                smp = obj()
                if smp.__dict__.get("enable", settings.default_enable_sample):
                    settings.samples[name] = smp
    return len(settings.samples) - old_len
