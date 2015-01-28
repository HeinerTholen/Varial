import inspect
import itertools
import collections
import os.path
import glob

import monitor
import settings
import wrappers


class Sample(wrappers.WrapperBase):
    """
    Collect information about a sample.

    Either 'lumi' or 'x_sec' and 'n_events' must be given

    :param name:        str
    :param is_data:     bool (default: False)
    :param is_signal:   bool (default: False)
    :param lumi:        float
    :param x_sec:       float
    :param n_events:    int
    :param legend:      str (used to group samples as well, default: name)
    :param n_events:    int
    :param input_files: list of str

    Optional parameters for cmsRun configs:
    :param output_file:     str (event content out)
    :param cmsRun_builtin:  dict (variable to be attact to builtin of a config)
    :param cmsRun_add_lines: list of str (appended to cmsRun config)
    :param cmsRun_args:     list of str (command line arguments for cmsRun)
    """

    def __init__(self, **kws):
        self.__dict__.update({
            'is_data': False,
            'is_signal': False,
            'x_sec': 0.,
            'n_events': 0,
            'lumi': 0.,
            'legend': '',
            'input_files': [],
            'output_file': '',
            'cmsRun_builtin': {},
            'cmsRun_add_lines': [],
            'cmsRun_args': [],
        })
        self.__dict__.update(kws)
        # check/correct input
        assert(not(self.is_data and self.is_signal))  # both is forbidden!
        if not getattr(self, 'name', 0):
            self.name = self.__class__.__name__
        assert isinstance(self.cmsRun_add_lines, list)
        assert isinstance(self.cmsRun_args, list)
        assert isinstance(self.cmsRun_builtin, dict)
        assert (isinstance(self.input_files, list)
                or isinstance(self.input_files, tuple))
        if self.x_sec and self.n_events:
            self.lumi = self.n_events / float(self.x_sec)
        if not self.lumi:
            monitor.message(
                self.name,
                'WARNING lumi or (x_sec and n_events) seems to be undefined.'
            )
        if not self.legend:
            self.legend = self.name


def _check_n_load(field):
    if inspect.isclass(field) and issubclass(field, Sample):
        smp = field()
        if hasattr(smp, 'enable'):
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
            if name[0] == '_':
                continue
            field = getattr(module, name)
            try:                    # handle iterable
                for f in field:
                    samples.update(_check_n_load(f))
            except TypeError:       # not an iterable
                samples.update(_check_n_load(field))
    return samples


def generate_samples(in_filenames, in_path='', out_path=''):
    """
    Generates samples for analysis.all_samples.

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
        lambda t: 'file:' + t,  # prefix with 'file:' for cmssw
        in_filenames
    )
    return generate_samples(
        in_filenames, 
        '',
        out_path
    )

