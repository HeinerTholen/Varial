# generators.py

################################################################### utility ###
import collections
import itertools
import operator

def _iterableize(obj_or_iterable):
    """provides iterable for [obj OR iterable(obj)]"""
    if isinstance(obj_or_iterable, collections.Iterable):
        for o in obj_or_iterable:
            yield o
    else:
        yield obj_or_iterable

def _filt_req(wrp, filter_dict): # generator over True/False
    for key, value in filter_dict.iteritems():
        try:
            yield getattr(wrp,key," ") in value # handle iterable
        except TypeError:
            if hasattr(value, "search"):
                yield bool(value.search(getattr(wrp,key," ")))
            else:
                yield getattr(wrp,key," ") == value # handle non-iterable

def debug_printer(iterable, print_obj=True):
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
                "name"      : re.compile("histo*")   # regular expression
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

def callback(wrps, filter_dict=None, func=None):
    """
    Do a special treatment for selected wrps! All wrps are yielded.

    :param wrps:        Wrapper iterable
    :param filter_dict: same as key_value_dict in ``filter(..)`` above
    :param func:        callable
    :yields:            Wrapper

    **Example:** If you wanted to color all passing MC histograms blue::

        def make_blue(wrp):
            wrp.histo.SetFillColor(ROOT.kBlue)
            return wrp # IMPORTANT! RETURN THE WRAPPER!

        callback(
            wrappers,
            {"is_data": False}
            make_blue
        )
    """
    if not func:
        for wrp in wrps:
            yield wrp
    else:
        if not filter_dict: filter_dict = {}
        for wrp in wrps:
            if all(_filt_req(wrp, filter_dict)):
                wrp = func(wrp)
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

    **Example:** The ``lumi`` and ``int`` operations are generatorized below
    (notice that ``w1``,``w2`` and ``w3`` are iterables):

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
    >>> gen_int = generate_op(op.int)
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
gen_mv_in = generate_op(op.mv_in)  #: This is ``generate_op(cmstoolsac3b.operations.mv_in)``
gen_int   = generate_op(op.int)    #: This is ``generate_op(cmstoolsac3b.operations.int)``
gen_int_l = generate_op(op.int_l)  #: This is ``generate_op(cmstoolsac3b.operations.int_l)``
gen_int_r = generate_op(op.int_r)  #: This is ``generate_op(cmstoolsac3b.operations.int_r)``

############################################################### load / save ###
import settings
import histodispatch as dsp
from ROOT import TFile

def fs_content():
    """
    Searches ``settings.DIR_FILESERVICE`` for samples and loads aliases.

    :yields:   FileServiceAlias
    """
    for alias in dsp.HistoDispatch().fileservice_aliases():
        yield alias

def pool_content(filter_dict=None):
    """
    Yields selected pool content.

    :param filter_dict: same as key_value_dict in ``filter(..)`` above
    :yields:    Wrappers
    """
    return filter(dsp.HistoPool().get(), filter_dict)

def pool_store_items(wrps):
    """
    Saves items in pool and yields them again.

    :param wrps:    Wrapper iterable
    :yields:        Wrapper
    """
    pool = dsp.HistoPool()
    for wrp in wrps:
        for w in _iterableize(wrp):
            pool.put(w)
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
    hd = dsp.HistoDispatch()
    for alias in aliases:
        yield hd.load_histogram(alias)

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
            [.root, .png]           # BETTER: settings.rootfile_postfixes
        )
    """
    if not suffices: suffices = settings.rootfile_postfixes
    for wrp in wrps:
        if hasattr(wrp, "primary_object"):
            filename = filename_func(wrp)
            prim_obj = wrp.primary_object()
            for suffix in suffices:
                prim_obj.SaveAs(filename + suffix)
            if hasattr(wrp, "write_info_file"):
                wrp.write_info_file(filename + ".info")
        yield wrp

################################################### application & packaging ###
import rendering as rnd

def apply_histo_fillcolor(wrps):
    """
    Uses ``histo.SetFillColor``. Colors from utilities.settings

    :param wrps:    HistoWrapper iterable
    :yields:        HistoWrapper
    """
    for wrp in wrps:
        if hasattr(wrp, "histo"):
            fill_color = settings.get_fill_color(wrp.sample)
            if fill_color:
                wrp.histo.SetFillColor(fill_color)
        yield wrp

def fs_filter_sort_load(filter_dict=None, key_list=None):
    """
    Packaging of filtering, sorting and loading.

    **Implementation:** ::

        wrps = fs_content()
        wrps = filter(wrps, filter_dict)
        wrps = sort(wrps, key_list)
        return load(wrps)
    """
    wrps = fs_content()
    wrps = filter(wrps, filter_dict)
    wrps = sort(wrps, key_list)
    return load(wrps)

def fs_mc_stack(filter_dict=None, merge_mc_key_func=None):
    """Delivers only MC stacks, no data, from fileservice."""
    if not merge_mc_key_func:
        merge_mc_key_func = lambda w: settings.get_stack_position(w.sample)
    loaded = fs_filter_sort_load(filter_dict)
    grouped = group(loaded)
    for grp in grouped:

        # merge mc samples (merge also normalizes to lumi = 1.)
        mc_sorted = sorted(grp, key=merge_mc_key_func)
        mc_groupd = group(mc_sorted, merge_mc_key_func)
        mc_merged = (op.merge(g) for g in mc_groupd)
        mc_colord = apply_histo_fillcolor(mc_merged)

        # stack mc
        mc_stack = op.stack(mc_colord)
        yield (mc_stack,)

def fs_mc_stack_n_data_sum(filter_dict=None, merge_mc_key_func=None):
    """
    The full job to stacked histos and data, directly from fileservice.

    Check out the sourcecode!
    """
    if not merge_mc_key_func:
        merge_mc_key_func = lambda w: settings.get_stack_position(w.sample)
    loaded = fs_filter_sort_load(filter_dict)

    # group by analyzer_histo (the fs histo 'ID')
    grouped = group(loaded)
    for grp in grouped:

        # split stream
        data, mc = split_data_mc(grp)

        # sum up data
        data_sum = op.sum(data)
        data_lumi = op.lumi(data_sum)

        # merge mc samples (merge also normalizes to lumi = 1.)
        mc_sorted = sorted(mc, key=merge_mc_key_func)
        mc_groupd = group(mc_sorted, merge_mc_key_func)
        mc_merged = (op.merge(g) for g in mc_groupd)
        mc_colord = apply_histo_fillcolor(mc_merged)

        # stack mc
        mc_norm = gen_prod(itertools.izip(mc_colord, itertools.repeat(data_lumi)))
        mc_stack = op.stack(mc_norm)
        yield mc_stack, data_sum

def make_canvas_builder(grps):
    """
    Yields instanciated CanvasBuilders.

    :param grps:    grouped(!) Wrapper iterable
    :yields:        CanvasBuilder instance
    """
    for grp in grps:
        yield rnd.CanvasBuilder(grp)

def decorate(wrps, decorators = list()):
    """
    Decorate any iterable with a list of decorators.

    :param wrps:        Wrapper (or CanvasBuilder) iterable
    :param decorators:  list of decorator classes.
    :yields:            Wrapper (or CanvasBuilder)

    **Example:** ::

        result = decorate([CanvasBuilder, ...], [Legend, TextBox])
        # result = [Legend(TextBox(CanvasBuilder)), ...]
    """
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

def canvas(grps, 
           decorators=list(), 
           callback_filter=None, 
           callback_func=None):
    """
    Packaging of canvas builder, decorating, callback and canvas building.

    **Implementation:** ::

        grps = make_canvas_builder(grps)
        grps = decorate(grps, decorators)
        grps = callback(grps, filter_dict=callback_filter, func=callback_func)
        return build_canvas(grps)
    """
    def put_ana_histo_name(grps):
        for grp in grps:
            if hasattr(grp.renderers[0], "analyzer"):
                grp.name = grp.renderers[0].analyzer+"_"+grp.name
            yield grp
    grps = make_canvas_builder(grps)
    grps = put_ana_histo_name(grps)
    grps = decorate(grps, decorators)
    grps = callback(grps, filter_dict=callback_filter, func=callback_func)
    return build_canvas(grps)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
