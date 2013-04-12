"""
An example Sample definition.
"""

import cmstoolsac3b.sample as smp

common_input_path   = "/the/path/to/all/input/files/"
common_output_path  =  "/a/folder/for/all/eventoutput/"


class FirstMCSample(smp.Sample):
    """Shortest possible Declaration"""
    input_files = [common_input_path + "some/dir/qcd*.root"] #: specify input files. Globbing is use, so '*' is fine.
    lumi        = 50000.                                     #: Luminosity: Unit has to be consistent over all samples.


class TheDataSample(smp.Sample):
    """Data sample: notice 'is_data'!"""
    input_files = [common_input_path + "data/dir/*.root"]
    lumi        = 4700.
    output_file = common_output_path
    legend      = "Data"
    is_data     = True                                      #: set this to 'True' for data samples.


class OtherMCSample(smp.Sample):
    """Extensive Declaration"""
    enable          = True                                  #: Force usage. Also see settings.default_enable_sample
    input_files     = [common_input_path + "some/dir/muon*.root"]
    n_events        = 1000000                               #: either 'n_events' and 'x_sec' or 'lumi' has to be provided.
    x_sec           = 165.                                  #: cross section
    output_file     = common_output_path                    #: if not ends on '.root' 'samplename.root' is appended
    legend          = "t#bart Inclusive"                    #: legend string: Many samples can have the same.
    cfg_builtin     = {                                     #: added to the builtin dict cms_var
        "some_string": "\"a_string\"",
        "some_number": 12.345
    }
    cfg_add_lines   = [                                     #: code lines to be appended to the cfg
        "print \"these code lines are appended to\"",
        "print \"the sample-specific cfg file.\""
    ]
    cmsRun_args     = "this is passed to cmsRun execution"  #: can be string or list of strings

