import itertools
import os
import time
import ROOT

import analysis
import generators as gen
import rendering
import settings
import toolinterface


def rename_th2(wrps):
    for wrp in wrps:
        if 'TH2' in wrp.type:
            wrp.name += '_' + wrp.legend
            wrp.in_file_path += '_' + wrp.legend
        yield wrp


def set_canvas_name_to_infilepath(grps):
    for grp in grps:
        grp.name = grp.renderers[0].in_file_path.replace('/', '_')
        yield grp


def set_canvas_name_to_plot_name(grps):
    for grp in grps:
        grp.name = grp.renderers[0].name
        yield grp


def plot_grouper_by_in_file_path(wrps, separate_th2=True):
    if separate_th2:
        wrps = rename_th2(wrps)
    return gen.group(wrps, key_func=lambda w: w.in_file_path)


def plot_grouper_by_number_of_plots(wrps, n_per_group):
    class GroupKey(object):
        def __init__(self, n_per_group):
            self.n_th_obj = -1
            self.n_per_group = n_per_group
        def __call__(self, _):
            self.n_th_obj += 1
            return self.n_th_obj / self.n_per_group
    return gen.group(wrps, GroupKey(n_per_group))


def overlay_colorizer(wrps, colors=None):
    wrps = gen.apply_linecolor(wrps, colors)
    for w in wrps:
        w.histo.SetFillStyle(0)
        yield w


def default_plot_colorizer(grps, colors=None):
    grps = (gen.apply_linecolor(ws, colors) for ws in grps)
    grps = (gen.apply_markercolor(ws, colors) for ws in grps)
    return grps


default_canvas_decorators = [
    rendering.BottomPlotRatioSplitErr,
    rendering.Legend
]


class Plotter(toolinterface.Tool):
    """
    A plotter. Makes stacks and overlays data by default.

    Overriding set_up_content and setting self.stream_content lets
    Default attributes, that can be overwritten by init keywords:

    >>> defaults = {
    ...    'input_result_path': None,
    ...    'filter_keyfunc': None,
    ...    'load_func': gen.fs_filter_active_sort_load,
    ...    'hook_loaded_histos': None,
    ...    'stack_grouper': plot_grouper_by_in_file_path,
    ...    'plot_grouper': lambda wrps: ((w,) for w in wrps),
    ...    'stack_setup': lambda w: gen.mc_stack_n_data_sum(w, None, True),
    ...    'plot_setup': default_plot_colorizer,
    ...    'hook_canvas_pre_build': None,
    ...    'hook_canvas_post_build': None,
    ...    'save_log_scale': False,
    ...    'save_lin_log_scale': False,
    ...    'keep_content_as_result': False,
    ...    'set_canvas_name': set_canvas_name_to_infilepath,
    ...    'save_name_func': lambda wrp: wrp.name,
    ...    'canvas_decorators': default_canvas_decorators,
    ...}
    """
    defaults_attrs = {
        'input_result_path': None,
        'filter_keyfunc': None,
        'load_func': gen.fs_filter_active_sort_load,
        'hook_loaded_histos': None,
        'stack_grouper': plot_grouper_by_in_file_path,
        'plot_grouper': lambda wrps: ((w,) for w in wrps),
        'stack_setup': lambda w: gen.mc_stack_n_data_sum(w, None, True),
        'plot_setup': default_plot_colorizer,
        'hook_canvas_pre_build': None,
        'hook_canvas_post_build': None,
        'save_log_scale': False,
        'save_lin_log_scale': False,
        'keep_content_as_result': False,
        'set_canvas_name': set_canvas_name_to_infilepath,
        'save_name_func': lambda wrp: wrp.name,
        'canvas_decorators': default_canvas_decorators,
    }

    class NoFilterDictError(Exception):
        pass

    def __init__(self, name=None, stack=False, **kws):
        super(Plotter, self).__init__(name)
        defaults = dict(self.defaults_attrs)
        defaults.update(self.__dict__)  # do not overwrite user stuff
        defaults.update(kws)            # add keywords
        self.__dict__.update(defaults)  # set attributes in place
        self.stream_content = None
        if stack:
            self.plot_setup = self.stack_setup
            self.plot_grouper = self.stack_grouper

    def configure(self):
        pass

    def load_content(self):
        if self.input_result_path:
            wrps = self.lookup_result(self.input_result_path)
            if not wrps:
                raise RuntimeError(
                    'ERROR Input not found: "%s"' % self.input_result_path)
        else:
            wrps = self.lookup_result('../HistoLoader')
        if wrps:
            if self.filter_keyfunc:
                wrps = itertools.ifilter(self.filter_keyfunc, wrps)
        else:
            if not self.filter_keyfunc:
                self.message('WARNING No filter_keyfunc set! '
                             'Working with _all_ histograms.')
            wrps = self.load_func(self.filter_keyfunc)
        if self.hook_loaded_histos:
            wrps = self.hook_loaded_histos(wrps)
        self.stream_content = list(wrps)
        if not self.stream_content:
            self.message('WARNING Could not load histogram content!')

    def group_content(self):
        wrps = self.stream_content
        if self.plot_grouper:
            wrps = list(self.plot_grouper(wrps))
        self.stream_content = list(wrps)
        if not self.stream_content:
            self.message('WARNING Could not group histogram content!')

    def setup_content(self):
        wrps = self.stream_content
        if self.plot_setup:
            wrps = self.plot_setup(wrps)
        self.stream_content = list(wrps)
        if not self.stream_content:
            self.message('WARNING Could not setup histogram content!')

    def store_content_as_result(self):
        if self.keep_content_as_result:
            self.stream_content = list(self.stream_content)
            self.result = list(
                itertools.chain.from_iterable(self.stream_content))

    def make_canvases(self):
        def run_build_procedure(bldr):
            for b in bldr:
                b.run_procedure()
                yield b

        def decorate(bldr):
            for b in bldr:
                if not (hasattr(b.renderers[0], 'histo') and
                        isinstance(b.renderers[0].histo, ROOT.TH2D)):
                    for dec in self.canvas_decorators:
                        b = dec(b)
                yield b

        bldr = gen.make_canvas_builder(self.stream_content)
        bldr = self.set_canvas_name(bldr)
        bldr = decorate(bldr)
        if self.hook_canvas_pre_build:
            bldr = self.hook_canvas_pre_build(bldr)
        bldr = run_build_procedure(bldr)
        if self.hook_canvas_post_build:
            bldr = self.hook_canvas_post_build(bldr)

        # no list and warning here, since canvases would be deleted if the have
        # the same name. This way, diskio will tell if a file is overwritten.
        self.stream_content = gen.build_canvas(bldr)

    def save_canvases(self):
        if self.save_lin_log_scale:
            self.stream_content = gen.save_canvas_lin_log(
                self.stream_content,
                self.save_name_func,
            )
        else:
            if self.save_log_scale:
                self.stream_content = gen.switch_log_scale(self.stream_content)
            self.stream_content = gen.save(
                self.stream_content,
                self.save_name_func,
            )
        count = gen.consume_n_count(self.stream_content)
        level = "INFO" if count else "WARNING"
        self.message("%s %s produced %d canvases." % (level, self.name, count))

    def run(self):
        self.configure()
        self.load_content()
        self.group_content()
        self.setup_content()
        self.store_content_as_result()
        self.make_canvases()
        self.save_canvases()


class RootFilePlotter(toolinterface.ToolChainParallel):
    """
    Plots all histograms in a rootfile.

    **NOTE: please use the** ``tools.mk_rootfile_plotter`` **function!**

    :param pattern:             str, search pattern for rootfiles
    :param plotter_factory:     factory function for RootFilePlotter
                                default: ``None``
    :param flat:                bool, flatten the rootfile structure
                                default: ``False``
    :param name:                str, tool name
    """

    def _setup_aliases(self, pattern, filter_keyfunc):
        aliases = gen.dir_content(pattern)
        if not aliases:
            self.message('WARNING Could not create aliases for plotting.')
        else:
            aliases = itertools.ifilter(
                lambda a: type(a.type) == str and (
                    a.type.startswith('TH') or a.type == 'TProfile'
                ),
                aliases
            )
            aliases = itertools.ifilter(filter_keyfunc, aliases)
            aliases = sorted(
                aliases,
                key=lambda a: a.in_file_path
            )
        self.aliases = aliases

    @staticmethod
    def _setup_legendnames_from_files(pattern):
        filenames = gen.resolve_file_pattern(pattern)

        # only one file: return directly
        if len(filenames) < 2:
            return {filenames[0]: filenames[0]}

        # try the sframe way:
        # TODO make setting for that!!
        lns = list(n.split('.') for n in filenames if type(n) is str)
        if all(len(l) == 5 for l in lns):
            return dict((f, l[3]) for f, l in itertools.izip(filenames, lns))

        # TODO at least 10 characters
        # try trim filesnames from front and back
        lns = filenames[:]
        try:
            while all(n[0] == lns[0][0] for n in lns):
                for i in xrange(len(lns)):
                    lns[i] = lns[i][1:]
            while all(n[-1] == lns[0][-1] for n in lns):
                for i in xrange(len(lns)):
                    lns[i] = lns[i][:-1]
        except IndexError:
            return dict((f, f) for f in filenames[:])
        return dict((f, l) for f, l in itertools.izip(filenames, lns))

    def _setup_gen_legend(self, pattern, legendnames=None):
        if not legendnames:
            legendnames = self._setup_legendnames_from_files(pattern)
        legendnames = dict((os.path.basename(p), l)
                           for p, l in legendnames.iteritems())
        self.message(
            'INFO  Legend names that I will use if not overwritten:\n'
            + '\n'.join('%32s: %s' % (v,k) for k,v in legendnames.iteritems())
        )

        def gen_apply_legend(wrps):
            for w in wrps:
                if not w.legend:
                    w.legend = legendnames[os.path.basename(w.file_path)]
                yield w
        return gen_apply_legend

    def __init__(self,
                 pattern,
                 plotter_factory=None,
                 flat=False,
                 name=None,
                 filter_keyfunc=None,
                 legendnames=None):
        super(RootFilePlotter, self).__init__(name)

        # initialization for all instances
        self._private_plotter = None
        self._is_base_instance = bool(pattern)
        if not self._is_base_instance:
            return

        # initialization for base instance only
        if settings.use_parallel_chains and settings.max_num_processes > 1:
            self.message('INFO Using parallel plotting. Disable with '
                         '"varial.settings.use_parallel_chains = False"')
        ROOT.gROOT.SetBatch()
        if not plotter_factory:
            plotter_factory = Plotter

        self._setup_aliases(pattern, filter_keyfunc)
        gen_apply_legend = self._setup_gen_legend(pattern, legendnames)

        # either print all in one dir...
        if flat:
            self._private_plotter = plotter_factory(
                name=self.name,
                filter_keyfunc=lambda _: True,
                load_func=lambda _: gen_apply_legend(
                    gen.load(gen.fs_content())),
                plot_grouper=plot_grouper_by_in_file_path,
                plot_setup=lambda ws: gen.mc_stack_n_data_sum(
                    ws, lambda w: '', True),
                save_name_func=lambda w:
                    w._renderers[0].in_file_path.replace('/', '_'),
                canvas_decorators=[rendering.Legend],
            )

        # ...or resemble root file dirs
        else:
            for path in (a.in_file_path for a in self.aliases):
                rfp = self
                path = path.split('/')

                # make RootFilePlotters for dirs if not in basedir
                if len(path) > 1:
                    for folder in path[:-1]:
                        if not folder in rfp.tool_names:
                            rfp.add_tool(RootFilePlotter(
                                None, plotter_factory, name=folder))
                        rfp = rfp.tool_names[folder]

                # make plotter instance if not done already
                if not rfp._private_plotter:
                    def _mk_private_loader(p):
                        # This function creates a separate namespace for p
                        # (the last reference to p would be lost otherwise)
                        def loader(filter_keyfunc):
                            wrps = analysis.fs_aliases
                            wrps = itertools.ifilter(
                                lambda w: w.in_file_path.split('/')[:-1] == p
                                          and filter_keyfunc(w),
                                wrps
                            )
                            wrps = gen.load(wrps)
                            wrps = gen_apply_legend(wrps)
                            return wrps
                        return loader

                    rfp._private_plotter = plotter_factory(
                        name=self.name,
                        filter_keyfunc=lambda _: True,
                        plot_grouper=plot_grouper_by_in_file_path,
                        set_canvas_name=set_canvas_name_to_plot_name,
                        load_func=_mk_private_loader(path[:-1]),
                        canvas_decorators=[rendering.Legend],
                    )

    def run(self):
        time.sleep(1)  # weird bug in root...
        old_aliases = analysis.fs_aliases
        if self._is_base_instance:
            analysis.fs_aliases = self.aliases
        super(RootFilePlotter, self).run()
        if self._private_plotter:
            logfile = '%s/.pltr_done' % analysis.cwd
            if self._reuse and os.path.exists(logfile):
                self.message('INFO reusing...')
            else:
                if os.path.exists(logfile):
                    os.remove(logfile)
                self._parallel_worker_start()
                self._private_plotter.run()
                self._parallel_worker_done()
                with open(logfile, 'w') as f:
                    f.write('plotter done.\n')
        if self._is_base_instance:
            analysis.fs_aliases = old_aliases
