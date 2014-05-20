"""
This module containes all analysis specific information and various helpers.
"""

import settings


################################################################### samples ###
import wrappers
active_samples = []  # list of samplenames without systematic samples


def mc_samples():
    """Returns a dict of all MC samples."""
    return dict(
        (k, v)
        for k, v in settings.all_samples.iteritems()
        if k in active_samples and not v.is_data
    )


def data_samples():
    """Returns a dict of all real data samples."""
    return dict(
        (k, v)
        for k, v in settings.all_samples.iteritems()
        if k in active_samples and v.is_data
    )


def data_lumi_sum():
    """Returns the sum of luminosity in data samples."""
    return float(sum(
        v.lumi
        for k, v in data_samples().iteritems()
        if k in active_samples
    ))


def data_lumi_sum_wrp():
    """Returns the sum of data luminosity in as a FloatWrapper."""
    return wrappers.FloatWrapper(data_lumi_sum(), history="DataLumiSum")


def get_pretty_name(key):
    """Simple dict call for names, e.g. axis labels."""
    return settings.pretty_names.get(key, key)


def get_color(sample_or_legend_name):
    """Gives a ROOT color value back for sample or legend name."""
    name = sample_or_legend_name
    s = settings
    if name in s.colors:
        return s.colors[name]
    elif name in s.all_samples:
        return s.colors.get(s.all_samples[name].legend)


def get_stack_position(sample):
    """Returns the stacking position (integer)"""
    s = settings
    legend = s.all_samples[sample].legend
    if legend in s.stacking_order:
        return str(s.stacking_order.index(legend) * 0.001)  # needs be string
    else:                                                   #
        return legend                                       # to be comparable


########################################################### tool management ###


#todo get_tool_abs(string)
#todo get_tool_rel(string)
#todo or similar with __getattr__