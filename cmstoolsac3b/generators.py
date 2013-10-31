# generators.py

################################################################### utility ###
import collections
import itertools
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

def _filt_items(wrp, key, value_list):
    """yields True/False for every value in value_list"""
    for val in value_list:
        try:
            yield bool(val.search(getattr(wrp,key," ")))
        except AttributeError:
            yield getattr(wrp,key," ") == val

def _filt_req(wrp, filter_dict):
    """Yields True/False for each item in filter_dict"""
    for key, value in filter_dict.iteritems():
        value = _iterableize(value)
        yield any(_filt_items(wrp, key, value))

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
    for obj in iterable:
        count += 1
    return count

def filter(wrps, key_value_dict=None):
    """
    Only wrappers with specified attributes can pass this generator.

    :param  wrps:           Wrapper iterable
    :param  key_value_dict: dictionary of attributes, see cmstoolsac3b_example
    :yields:                Wrapper

    **Example:** (Every key in the given dictonairy is tested, where the key
    is the tested attribute of the wrapper. A single value, a list of values or
    a regular expression can be evaluated)::

        filter(
            wrappers,
            {
                "is_data"   : False,                # single value
                "analyzer"  : ["AnaEt", "AnaDR"]    # candidate list
                "name"      : re.compile("histo")   # regular expression
            }
        )

    If the **key_value_dict** is empty, all wrappers pass the filter.
    """
    if not key_value_dict: key_value_dict = {}
    assert type(key_value_dict) == dict
    return itertools.ifilter(
        lambda wrp: all(_filt_req(wrp, key_value_dict)),
        wrps
    )

def rejector(wrps, key_value_dict=None):
    """Just as filter, only rejects items with the given properites."""
    if not key_value_dict: key_value_dict = {}
    assert type(key_value_dict) == dict
    return itertools.ifilter(
        lambda wrp: not any(_filt_req(wrp, key_value_dict)),
        wrps
    )

def filter_active_samples(wrps):
    return itertools.ifilter(
        lambda w: w.sample in settings.active_samples,
        wrps
    )

def callback(wrps, func=None, filter_dict=None):
    """
    Do a special treatment for selected wrps! All wrps are yielded.

    :param wrps:        Wrapper iterable
    :param filter_dict: same as key_value_dict in ``filter(..)`` above
    :param func:        callable
    :yields:            Wrapper

    **Example:** If you wanted to color all passing MC histograms blue::

        def make_blue(wrp):
            wrp.histo.SetFillColor(ROOT.kBlue)

        callback(
            wrappers,
            make_blue
            {"is_data": False}
        )
    """
    if not func:
        for wrp in wrps:
            yield wrp
    else:
        if not filter_dict: filter_dict = {}
        for wrp in wrps:
            if all(_filt_req(wrp, filter_dict)):
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
    if not key_list: key_list = ['analyzer', 'name', 'is_data', 'sample']
    # python sorting is stable: Just sort by reversed key_list:
    for key in reversed(list(_iterableize(key_list))):
        wrps = sorted(wrps, key=operator.attrgetter(key))
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
    if not key_func: key_func = lambda w: w.analyzer+"_"+w.name
    for k,g in itertools.groupby(wrps, key_func):
        yield g

def interleave(*grouped_wrps):
    """
    Like itertools.izip, but chains inner packaging. Useful before making canvasses.

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
    data         = itertools.ifilter(lambda w: w.is_data, wrp_a)
    mcee         = itertools.ifilter(lambda w: not w.is_data, wrp_b)
    return data, mcee

def debug_print(wrps, prefix="DEBUG "):
    """
    Prints all passing items.

    **Implementation:** ::

        for wrp in wrps:
            print prefix, wrp.all_info()
            yield wrp
    """
    for wrp in wrps:
        print prefix, wrp.all_info()
        yield wrp

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
    >>> from cmstoolsac3b.wrappers import HistoWrapper
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
    >>> w4 = list(gen_int(w1, useBinWidth=True))
    >>> w4[0].float
    4.0
    """
    def gen_op(wrps, **kws):
        for wrp in wrps:
            yield op_func(wrp, **kws)
    return gen_op

gen_stack = generate_op(op.stack)  #: This is ``generate_op(cmstoolsac3b.operations.stack)``
gen_sum   = generate_op(op.sum)    #: This is ``generate_op(cmstoolsac3b.operations.sum)``
gen_merge = generate_op(op.merge)  #: This is ``generate_op(cmstoolsac3b.operations.merge)``
gen_prod  = generate_op(op.prod)   #: This is ``generate_op(cmstoolsac3b.operations.prod)``
gen_div   = generate_op(op.div)    #: This is ``generate_op(cmstoolsac3b.operations.div)``
gen_lumi  = generate_op(op.lumi)   #: This is ``generate_op(cmstoolsac3b.operations.lumi)``
gen_norm_to_lumi  = generate_op(op.norm_to_lumi)   #: This is ``generate_op(cmstoolsac3b.operations.norm_to_lumi)``
gen_norm_to_integral = generate_op(op.norm_to_integral)   #: This is ``generate_op(cmstoolsac3b.operations.norm_to_integral)``
gen_copy = generate_op(op.copy)   #: This is ``generate_op(cmstoolsac3b.operations.copy)``
gen_mv_in = generate_op(op.mv_in)  #: This is ``generate_op(cmstoolsac3b.operations.mv_in)``
gen_integral   = generate_op(op.integral)    #: This is ``generate_op(cmstoolsac3b.operations.integral)``
gen_int_l = generate_op(op.int_l)  #: This is ``generate_op(cmstoolsac3b.operations.int_l)``
gen_int_r = generate_op(op.int_r)  #: This is ``generate_op(cmstoolsac3b.operations.int_r)``

def gen_norm_to_data_lumi(wrps):
    return gen_prod(
        itertools.izip(
            gen_norm_to_lumi(wrps),
            itertools.repeat(settings.data_lumi_sum_wrp())
        )
    )

############################################################### load / save ###
import os
import settings
from ROOT import TFile

def fs_content():
    """
    Searches ``settings.DIR_FILESERVICE`` for samples and yields aliases.

    :yields:   FileServiceAlias
    """
    for alias in diskio.fileservice_aliases():
        yield alias

#TODO get able to load dir content!!!!
def dir_content(dir_path):
    """
    Searches directory for loadable wrapper-types. Yields aliases.

    :yields:   FileServiceAlias
    """
    basenames = []
    for cwd, dirs, files in os.walk(dir_path):
        for f in files:
            if (f[-5:] == ".info"
                and f[:-5] + ".root" in files):
                    basenames.append(f[:-5])
        break

def pool_content():
    """
    Yields all pool content.

    :yields:    Wrappers
    """
    return (w for w in settings.histo_pool)

def pool_store_items(wrps, callback = None):
    """
    Saves items in pool and yields them again.

    :param wrps:    Wrapper iterable
    :yields:        Wrapper
    """
    for wrp in wrps:
        for w in _iterableize(wrp):
            if callback:
                callback(w)
            settings.histo_pool.append(w)
        yield wrp

def pool_consume_n_count(wrps):
    """
    Consumes wrappers into pool.

    **Implementation:** ::

        return consume_n_count(pool_store_items(wrps))
    """
    return consume_n_count(pool_store_items(wrps))

def load(aliases):
    """
    Loads histograms in histowrappers for aliases.

    :param aliases: Alias iterable
    :yields:        HistoWrapper
    """
    for alias in aliases:
        yield diskio.load_histogram(alias)

def save(wrps, filename_func, suffices = None):
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
    if not suffices: suffices = settings.rootfile_postfixes
    for wrp in wrps:
        filename = filename_func(wrp)
        prim_obj = wrp.primary_object()
        for suffix in suffices:
            prim_obj.SaveAs(filename + suffix)
        diskio.write(wrp, filename)
        yield wrp

def get_from_post_proc_dict(key):
    """
    Yields from settings.post_proc_dict. Sets key as "post_proc_key" on items.
    """
    for w in settings.post_proc_dict.get(key, list()):
        w.post_proc_key = key
        yield w

################################################################## plotting ###
import rendering as rnd

def apply_histo_fillcolor(wrps, colors=None):
    """
    Uses ``histo.SetFillColor``. Colors from settings, if not given.

    :param wrps:    HistoWrapper iterable
    :param colors:  Integer list
    :yields:        HistoWrapper
    """
    n = 0
    for wrp in wrps:
        if hasattr(wrp, "histo"):
            if colors:
                color = colors[n%len(colors)]
                n += 1
            else:
                color = settings.get_color(wrp.sample)
            if color:
                wrp.histo.SetFillColor(color)
        yield wrp

def apply_histo_linecolor(wrps, colors=None):
    """
    Uses ``histo.SetLineColor``. Colors from settings, if not given.

    :param wrps:    HistoWrapper iterable
    :param colors:  Integer list
    :yields:        HistoWrapper
    """
    n = 0
    for wrp in wrps:
        if hasattr(wrp, "histo"):
            if colors:
                color = colors[n%len(colors)]
                n += 1
            else:
                color = settings.get_color(wrp.sample)
            if color:
                wrp.histo.SetLineColor(color)
        yield wrp

def apply_histo_linewidth(wrps, linewidth=2):
    """
    Uses ``histo.SetLineWidth``. Default is 2.

    :param wrps:        HistoWrapper iterable
    :param line_width:  argument for SetLineWidth
    :yields:            HistoWrapper
    """
    for wrp in wrps:
        if hasattr(wrp, "histo"):
            wrp.histo.SetLineWidth(2)
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
        # result = [Legend(TextBox(CanvasBuilder)), ...]
    """
    if not decorators: decorators = {}
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
def fs_filter_sort_load(filter_dict=None, sort_keys=None):
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
    wrps = filter(wrps, filter_dict)
    wrps = sort(wrps, sort_keys)
    return load(wrps)

def fs_filter_active_sort_load(filter_dict=None, sort_keys=None):
    """
    Just as fs_filter_sort_load, but also filter for active samples.
    """
    wrps = fs_content()
    wrps = filter_active_samples(wrps)
    wrps = filter(wrps, filter_dict)
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
        merge_mc_key_func = lambda w: settings.get_stack_position(w.sample)
    for grp in wrps:

        # merge mc samples (merge also normalizes to lumi = 1.)
        mc_sorted = sorted(grp, key=merge_mc_key_func)
        mc_groupd = group(mc_sorted, merge_mc_key_func)
        mc_merged = (op.merge(g) for g in mc_groupd)
        mc_colord = apply_histo_fillcolor(mc_merged)

        # stack mc
        stack = op.stack(mc_colord)
        yield stack

def fs_mc_stack(filter_dict=None, merge_mc_key_func=None):
    """
    Delivers only MC stacks, no data, from fileservice.

    :param filter_dict:         see function filter(...) above
    :param merge_mc_key_func:   key function for python sorted(...), default
                                tries to sort after stack position
    :yields:                    StackWrapper
    """
    loaded = fs_filter_active_sort_load(filter_dict)
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
        merge_mc_key_func = lambda w: settings.get_stack_position(w.sample)

    for grp in wrps:

        # split stream
        data, mc = split_data_mc(grp)

        # sum up data
        data_sum = None
        try:
            data_sum = op.sum(data)
        except op.TooFewWrpsError:
            print "WARNING generators.mc_stack_n_data_sum(..): "\
                  "No data histos present! I will yield only mc."
        if use_all_data_lumi:
            data_lumi = settings.data_lumi_sum_wrp()
        else:
            data_lumi = op.lumi(data_sum)

        # merge mc samples (merge also normalizes to lumi = 1.)
        mc_sorted = sorted(mc, key=merge_mc_key_func)
        mc_groupd = group(mc_sorted, merge_mc_key_func)
        mc_merged = (op.merge(g) for g in mc_groupd)
        mc_colord = apply_histo_fillcolor(mc_merged)

        # stack mc
        mc_norm = gen_prod(itertools.izip(mc_colord, itertools.repeat(data_lumi)))
        mc_stck = None
        try:
            mc_stck = op.stack(mc_norm)
        except op.TooFewWrpsError:
            print "WARNING generators.mc_stack_n_data_sum(..): " \
                  "No mc histos present! I will yield only data"
        if mc_stck and data_sum:
            yield mc_stck, data_sum
        elif mc_stck:
            yield (mc_stck, )
        elif data_sum:
            yield (data_sum, )
        else:
            raise op.TooFewWrpsError("Neither data nor mc histos present!")

def fs_mc_stack_n_data_sum(filter_dict=None, merge_mc_key_func=None):
    """
    The full job to stacked histos and data, directly from fileservice.

    The output are tuples of MC stacks and data histograms.
    ATTENTION: This crashes, if the proper histograms are not present!

    :param filter_dict:         see function filter(...) above
    :param merge_mc_key_func:   key function for python sorted(...), default
                                tries to sort after stack position
    :yields:                    (StackWrapper, HistoWrapper)
    """
    loaded = fs_filter_active_sort_load(filter_dict)
    grouped = group(loaded) # default: group by analyzer_histo (the fs histo 'ID')
    return mc_stack_n_data_sum(grouped, merge_mc_key_func, True)

def canvas(grps, 
           decorators=list()):
    """
    Packaging of canvas builder, decorating, callback and canvas building.

    :param grps:            grouped or ungrouped Wrapper iterable
                            if grouped: on canvas for each group
    :param decorators:      see function decorate(...) above
    :yields:                CanvasWrapper
    """
    def put_ana_histo_name(grps):
        for grp in grps:
            if hasattr(grp.renderers[0], "analyzer"):
                grp.name = grp.renderers[0].analyzer+"_"+grp.name
            yield grp
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
