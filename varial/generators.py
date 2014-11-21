# generators.py

################################################################### utility ###
import collections
import itertools

import analysis
import operator
import diskio


def _iterableize(obj_or_iterable):
    """provides iterable for [obj OR iterable(obj)]"""
    if (isinstance(obj_or_iterable, collections.Iterable)
            and not type(obj_or_iterable) == str):
        for o in obj_or_iterable:
            yield o
    else:
        yield obj_or_iterable


def debug_printer(iterable, print_obj=True):
    """
    Print objects and their type on flying by. Object printing can be turned off.

    :param iterable:    An iterable with objects
    :yields:            same as input
    """
    for obj in iterable:
        print "DEBUG: debug_printer: obj type: ", type(obj)
        if print_obj:
            print "DEBUG: debug_printer: obj:      ", obj
        yield obj


def consume_n_count(iterable):
    """
    Walks over iterable and counts number of items.

    :returns:   integer
    """
    count = 0
    for _ in iterable:
        count += 1
    return count


def filter_active_samples(wrps):
    return itertools.ifilter(
        lambda w: not analysis.active_samples
                  or w.sample in analysis.active_samples,
        wrps
    )


def callback(wrps, func=None, filter_keyfunc=None):
    """
    Do a special treatment for selected wrps! All wrps are yielded.

    :param wrps:            Wrapper iterable
    :param filter_keyfunc:  callable with one argument
    :param func:            callable
    :yields:                Wrapper

    **Example:** If you wanted to color all passing MC histograms blue::

        def make_blue(wrp):
            wrp.histo.SetFillColor(ROOT.kBlue)

        callback(
            wrappers,
            make_blue,
            lambda w: not w.is_data
        )
    """
    if not func:
        for wrp in wrps:
            yield wrp
    elif not filter_keyfunc:
        for wrp in wrps:
            func(wrp)
            yield wrp
    else:
        for wrp in wrps:
            if filter_keyfunc(wrp):
                func(wrp)
            yield wrp


def sort(wrps, key_list=None):
    """
    Sort stream after items in key_list. Loads full stream into memory.

    :param wrps:        Wrapper iterable
    :param key_list:    (List of) token(s) after which the stream is sorted.
                        First item has highest importance. If ``None``, then
                        ``['analyzer', 'name', 'is_data', 'sample']`` is used.
    :returns:           sorted list of wrappers.
    """
    if not key_list:
        key_list = settings.wrp_sorting_keys
    # python sorting is stable: Just sort by reversed key_list:
    wrps = list(wrps)
    for key in reversed(list(_iterableize(key_list))):
        try:
            wrps = sorted(wrps, key=operator.attrgetter(key))
        except AttributeError:
            print 'INFO Sorting by "%s" failed.' % key
    return wrps


def group(wrps, key_func=None):
    """
    Clusters stream into groups. wrps should be sorted.

    :param wrps:        Wrapper iterable
    :param key_func:    callable to group the wrappers. If ``None``, then
                        ``lambda w: w.analyzer + "_" + w.name`` is used.
    :yields:            Wrapper

    **Example:** This is neccessary before stacking, in order to have only
    same-observable-histograms stacked together::

        # wrappers has the names ["h1", "h1", "h2", "h2"]
        wrappers = group(wrappers)
        # result is like: [ ("h1", "h1"), ("h2", "h2") ]
    """
    if not key_func:
        key_func = lambda w: w.analyzer+"_"+w.name
    for k, g in itertools.groupby(wrps, key_func):
        yield g


def interleave(*grouped_wrps):
    """
    Like itertools.izip, but chains inner packaging. Useful before canvasses.

    ((a,b),(c,d)), ((1,2),(3,4)) => ((a,b,1,2), (c,d,3,4))

    :param *grouped_wrps:   grouped iterators
    :yields:                generator object
    """
    zipped = itertools.izip(grouped_wrps)
    for grp in zipped:
        yield itertools.chain(*grp)


def split_data_mc(wrps):
    """
    Split stream into data and mc stream.

    :param wrps:        Wrapper iterable
    :returns:           two wrapper iterators: ``(stream_data, stream_mc)``
    """
    wrp_a, wrp_b = itertools.tee(wrps)
    data = itertools.ifilter(lambda w: w.is_data, wrp_a)
    mcee = itertools.ifilter(lambda w: not w.is_data, wrp_b)
    return data, mcee


################################################################ operations ###
import operations as op


def generate_op(op_func):
    """
    Transforms an operation with one argument into a generator.

    :param op_func: callable
    :returns:       generator

    **Example:** The ``lumi`` and ``integral`` operations are generatorized
    below (notice that ``w1``,``w2`` and ``w3`` are iterables):

    >>> from ROOT import TH1I
    >>> from varial.wrappers import HistoWrapper
    >>> h1 = TH1I("h1", "", 2, .5, 4.5)
    >>> h1.Fill(1)
    1
    >>> h1.Fill(3)
    2
    >>> w1 = [HistoWrapper(h1, lumi=2.)]
    >>> gen_lumi = generate_op(op.lumi)
    >>> w2 = list(gen_lumi(w1))
    >>> w2[0].float
    2.0
    >>> gen_int = generate_op(op.integral)
    >>> w3 = list(gen_int(w1))
    >>> w3[0].float
    2.0
    >>> w4 = list(gen_int(w1, use_bin_width=True))
    >>> w4[0].float
    4.0
    """
    def gen_op(wrps, *args, **kws):
        for wrp in wrps:
            yield op_func(wrp, *args, **kws)
    return gen_op

gen_stack               = generate_op(op.stack)
gen_sum                 = generate_op(op.sum)
gen_merge               = generate_op(op.merge)
gen_prod                = generate_op(op.prod)
gen_div                 = generate_op(op.div)
gen_lumi                = generate_op(op.lumi)
gen_norm_to_lumi        = generate_op(op.norm_to_lumi)
gen_norm_to_integral    = generate_op(op.norm_to_integral)
gen_copy                = generate_op(op.copy)
gen_mv_in               = generate_op(op.mv_in)
gen_rebin               = generate_op(op.rebin)
gen_trim                = generate_op(op.trim)
gen_integral            = generate_op(op.integral)
gen_int_l               = generate_op(op.int_l)
gen_int_r               = generate_op(op.int_r)
gen_eff                 = generate_op(op.eff)


def gen_norm_to_data_lumi(wrps):
    return gen_prod(
        itertools.izip(
            gen_norm_to_lumi(wrps),
            itertools.repeat(analysis.data_lumi_sum_wrp())
        )
    )


############################################################### load / save ###
import settings


def fs_content():
    """
    Searches for samples and yields aliases.

    :yields:   FileServiceAlias
    """
    for alias in analysis.fs_aliases:
        yield alias


def dir_content(dir_path="./"):
    """
    Proxy of diskio.generate_aliases(directory)

    :yields:   Alias
    """
    return diskio.generate_aliases(dir_path)


def load(aliases):
    """
    Loads histograms in histowrappers for aliases.

    :param aliases: Alias iterable
    :yields:        HistoWrapper
    """
    for alias in aliases:
        yield diskio.load_histogram(alias)


def save(wrps, filename_func, suffices=None):
    """
    Saves passing wrps to disk, plus .info file with the wrapper infos.

    :param wrps:            Wrapper iterable
    :param filename_func:   callable that returns path and filename without
                            suffix.
    :param suffices:        list of suffices

    **Example:** ::

        save(
            wrappers,
            lambda wrp: OUTPUT_DIR + wrp.name,
            [.root, .png]           # DEFAULT: settings.rootfile_postfixes
        )
    """
    if not suffices:
        suffices = settings.rootfile_postfixes
    for wrp in wrps:
        filename = filename_func(wrp)
        diskio.write(wrp, filename, suffices)
        yield wrp


################################################################## plotting ###
import rendering as rnd


def apply_fillcolor(wrps, colors=None):
    """
    Uses ``histo.SetFillColor``. Colors from settings, if not given.

    :param wrps:    HistoWrapper iterable
    :param colors:  Integer list
    :yields:        HistoWrapper
    """
    n = 0
    for wrp in wrps:
        if colors:
            color = colors[n%len(colors)]
            n += 1
        else:
            color = analysis.get_color(wrp.sample)
        if color:
            wrp.primary_object().SetFillColor(color)
        yield wrp


def apply_linecolor(wrps, colors=None):
    """
    Uses ``histo.SetLineColor``. Colors from settings, if not given.

    :param wrps:    HistoWrapper iterable
    :param colors:  Integer list
    :yields:        HistoWrapper
    """
    n = 0
    for wrp in wrps:
        if colors:
            color = colors[n%len(colors)]
            n += 1
        else:
            color = analysis.get_color(wrp.sample)
        if color:
            wrp.primary_object().SetLineColor(color)
        yield wrp


def apply_linewidth(wrps, linewidth=2):
    """
    Uses ``histo.SetLineWidth``. Default is 2.

    :param wrps:        HistoWrapper iterable
    :param line_width:  argument for SetLineWidth
    :yields:            HistoWrapper
    """
    for wrp in wrps:
        wrp.primary_object().SetLineWidth(linewidth)
        yield wrp


def apply_markercolor(wrps, colors=None):
    """
    Uses ``histo.SetMarkerColor``. Colors from settings, if not given.

    :param wrps:    HistoWrapper iterable
    :param colors:  Integer list
    :yields:        HistoWrapper
    """
    n = 0
    for wrp in wrps:
        if colors:
            color = colors[n%len(colors)]
            n += 1
        else:
            color = analysis.get_color(wrp.sample)
        if color:
            wrp.primary_object().SetMarkerColor(color)
        yield wrp


def make_canvas_builder(grps):
    """
    Yields instanciated CanvasBuilders.

    :param grps:    grouped or ungrouped Wrapper iterable
                    if grouped: on canvas for each group
    :yields:        CanvasBuilder instance
    """
    for grp in grps:
        grp = _iterableize(grp)
        yield rnd.CanvasBuilder(grp)


def decorate(wrps, decorators=None):
    """
    Decorate any iterable with a list of decorators.

    :param wrps:        Wrapper (or CanvasBuilder) iterable
    :param decorators:  list of decorator classes.
    :yields:            Wrapper (or CanvasBuilder)

    **Example:** ::

        result = decorate([CanvasBuilder, ...], [Legend, TextBox])
        # result = [TextBox(Legend(CanvasBuilder)), ...]
    """
    if not decorators:
        decorators = []
    for wrp in wrps:
        for dec in decorators:
            wrp = dec(wrp)
        yield wrp


def build_canvas(bldrs):
    """
    Calls the ``build_canvas()`` method and returns the result.

    :param bldrs:   CanvasBuilder iterable
    :yields:        CanvasWrapper
    """
    for bldr in bldrs:
        yield bldr.build_canvas()


def switch_log_scale(cnvs, y_axis=True, x_axis=False):
    """
    Sets main_pad in canvases to logscale.
    
    :param cnvs:    CanvasWrapper iterable
    :param x_axis:  boolean for x axis
    :param y_axis:  boolean for y axis
    :yields:        CanvasWrapper
    """
    for cnv in cnvs:
        assert isinstance(cnv, rnd.wrappers.CanvasWrapper)
        if x_axis:
            cnv.main_pad.SetLogx(1)
        else:
            cnv.main_pad.SetLogx(0)
        if y_axis:
            cnv.first_drawn.SetMinimum(cnv.y_min_gr_0 * 0.5)
            cnv.main_pad.SetLogy(1)
        else:
            cnv.first_drawn.SetMinimum(cnv.y_min)
            cnv.main_pad.SetLogy(0)
        yield cnv


################################################### application & packaging ###
from ROOT import TH2D


def fs_filter_sort_load(filter_keyfunc=None, sort_keys=None):
    """
    Packaging of filtering, sorting and loading.

    :param filter_dict: see function filter(...) above
    :param sort_keys:   see function sort(...) above
    :yields:            HistoWrapper

    **Implementation:** ::

        wrps = fs_content()
        wrps = filter(wrps, filter_dict)
        wrps = sort(wrps, key_list)
        return load(wrps)
    """
    wrps = fs_content()
    wrps = itertools.ifilter(filter_keyfunc, wrps)
    wrps = sort(wrps, sort_keys)
    return load(wrps)


def fs_filter_active_sort_load(filter_keyfunc=None, sort_keys=None):
    """
    Just as fs_filter_sort_load, but also filter for active samples.
    """
    wrps = fs_content()
    wrps = filter_active_samples(wrps)
    wrps = itertools.ifilter(filter_keyfunc, wrps)
    wrps = sort(wrps, sort_keys)
    return load(wrps)


def mc_stack(wrps, merge_mc_key_func=None):
    """
    Delivers only MC stacks, feed only with MC.

    :param wrps:                Iterables of HistoWrapper (grouped)
    :param merge_mc_key_func:   key function for python sorted(...), default
                                tries to sort after stack position
    :yields:                    StackWrapper
    """
    if not merge_mc_key_func:
        merge_mc_key_func = lambda w: analysis.get_stack_position(w.sample)
    for grp in wrps:

        # merge mc samples (merge also normalizes to lumi = 1.)
        mc_sorted = sorted(grp, key=merge_mc_key_func)
        mc_groupd = group(mc_sorted, merge_mc_key_func)
        mc_merged = (op.merge(g) for g in mc_groupd)
        mc_colord = apply_fillcolor(mc_merged)

        # stack mc
        stack = op.stack(mc_colord)
        yield stack


def fs_mc_stack(filter_keyfunc=None, merge_mc_key_func=None):
    """
    Delivers only MC stacks, no data, from fileservice.

    :param filter_dict:         see function filter(...) above
    :param merge_mc_key_func:   key function for python sorted(...), default
                                tries to sort after stack position
    :yields:                    StackWrapper
    """
    loaded = fs_filter_active_sort_load(filter_keyfunc)
    grouped = group(loaded)
    return mc_stack(grouped, merge_mc_key_func)


def mc_stack_n_data_sum(wrps, merge_mc_key_func=None, use_all_data_lumi=False):
    """
    Stacks MC histos and merges data, input needs to be sorted and grouped.

    The output are tuples of MC stacks and data histograms.
    ATTENTION: This crashes, if the proper histograms are not present!

    :param wrps:                Iterables of HistoWrapper (grouped)
    :param merge_mc_key_func:   key function for python sorted(...), default
                                tries to sort after stack position
    :yields:                    (StackWrapper, HistoWrapper)
    """
    if not merge_mc_key_func:
        merge_mc_key_func = lambda w: analysis.get_stack_position(w.sample)

    for grp in wrps:

        # split stream
        data, mc = split_data_mc(grp)

        # sum up data
        data_sum = None
        try:
            data_sum = op.sum(data)
        except op.TooFewWrpsError:
            print "INFO generators.mc_stack_n_data_sum(..): "\
                  "No data histos present! I will yield only mc."
        if data_sum and not use_all_data_lumi:
            data_lumi = op.lumi(data_sum)
        else:
            data_lumi = analysis.data_lumi_sum_wrp()

        # merge mc samples (merge also normalizes to lumi = 1.)
        mc_sorted = sorted(mc, key=merge_mc_key_func)
        mc_groupd = group(mc_sorted, merge_mc_key_func)
        mc_merged = (op.merge(g) for g in mc_groupd)
        mc_colord = apply_fillcolor(mc_merged)
        is_2d = mc_sorted and isinstance(mc_sorted[0].histo, TH2D)

        # stack mc
        mc_norm = gen_prod(itertools.izip(mc_colord,
                                          itertools.repeat(data_lumi)))
        mc_stck = None
        try:
            if is_2d:
                mc_stck = op.sum(mc_norm)
            else:
                mc_stck = op.stack(mc_norm)
        except op.TooFewWrpsError:
            print "INFO generators.mc_stack_n_data_sum(..): " \
                  "No mc histos present! I will yield only data"
        if mc_stck and data_sum:
            yield mc_stck, data_sum
        elif mc_stck:
            yield (mc_stck, )
        elif data_sum:
            yield (data_sum, )
        else:
            raise op.TooFewWrpsError("Neither data nor mc histos present!")


def fs_mc_stack_n_data_sum(filter_keyfunc=None, merge_mc_key_func=None):
    """
    The full job to stacked histos and data, directly from fileservice.

    The output are tuples of MC stacks and data histograms.
    ATTENTION: This crashes, if the proper histograms are not present!

    :param filter_dict:         see function filter(...) above
    :param merge_mc_key_func:   key function for python sorted(...), default
                                tries to sort after stack position
    :yields:                    (StackWrapper, HistoWrapper)
    """
    loaded = fs_filter_active_sort_load(filter_keyfunc)
    grouped = group(loaded)     # default: group by analyzer_histo
                                # (the fs histo 'ID')
    return mc_stack_n_data_sum(grouped, merge_mc_key_func, True)


def canvas(grps, decorators=None):
    """
    Packaging of canvas builder, decorating, callback and canvas building.

    :param grps:            grouped or ungrouped Wrapper iterable
                            if grouped: on canvas for each group
    :param decorators:      see function decorate(...) above
    :yields:                CanvasWrapper
    """
    def put_ana_histo_name(groups):
        for grp in groups:
            if hasattr(grp.renderers[0], "analyzer"):
                grp.name = grp.renderers[0].analyzer+"_"+grp.name
            yield grp
    if not decorators:
        decorators = []
    grps = make_canvas_builder(grps)            # a builder for every group
    grps = put_ana_histo_name(grps)             # only applies to fs histos
    grps = decorate(grps, decorators)           # apply decorators
    return build_canvas(grps)                   # and do the job


def save_canvas_lin_log(cnvs, filename_func):
    """
    Saves canvasses, switches to logscale, saves again.

    :param cnvs:            CanvasWrapper iterable
    :param filename_func:   see function save(...) above
    :yields:                CanvasWrapper
    """
    cnvs = save(
        cnvs,
        lambda c: filename_func(c) + "_lin"
    )
    cnvs = switch_log_scale(cnvs)
    cnvs = save(
        cnvs,
        lambda c: filename_func(c) + "_log"
    )
    return cnvs


if __name__ == "__main__":
    import doctest
    doctest.testmod()
