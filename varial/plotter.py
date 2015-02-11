import glob
import itertools
import os
import time
import ROOT

import analysis
import diskio
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


def plot_grouper_by_in_file_path(wrps, separate_th2=True):
    if separate_th2:
        wrps = rename_th2(wrps)
    return gen.group(wrps, key_func=lambda w: w.in_file_path)


def overlay_colorizer(wrps, colors=None):
    wrps = gen.apply_linecolor(wrps, colors)
    for w in wrps:
        w.histo.SetFillStyle(0)
        yield w


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
    ...    'plot_setup': lambda wrps: wrps,
    ...    'hook_canvas_pre_build': None,
    ...    'hook_canvas_post_build': None,
    ...    'save_log_scale': False,
    ...    'save_lin_log_scale': False,
    ...    'keep_content_as_result': False,
    ...    'save_name_func': lambda wrp: wrp.name,
    ...    'canvas_decorators': [
    ...        rendering.BottomPlotRatioSplitErr,
    ...        rendering.Legend
    ...    ]
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
        'plot_setup': lambda wrps: wrps,
        'hook_canvas_pre_build': None,
        'hook_canvas_post_build': None,
        'save_log_scale': False,
        'save_lin_log_scale': False,
        'keep_content_as_result': False,
        'save_name_func': lambda wrp: wrp.name,
        'canvas_decorators': [
            rendering.BottomPlotRatioSplitErr,
            rendering.Legend
        ]
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
        self.stream_canvas = None
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
                self.message("WARNING No filter_keyfunc set! "
                             "Working with _all_ histograms.")
            wrps = self.load_func(self.filter_keyfunc)
        if self.hook_loaded_histos:
            wrps = self.hook_loaded_histos(wrps)
        self.stream_content = wrps

    def set_up_content(self):
        wrps = self.stream_content
        if self.plot_grouper:
            wrps = self.plot_grouper(wrps)
        if self.plot_setup:
            wrps = self.plot_setup(wrps)
        self.stream_content = wrps

    def store_content_as_result(self):
        if self.keep_content_as_result:
            self.stream_content = list(self.stream_content)
            self.result = list(
                itertools.chain.from_iterable(self.stream_content))

    def set_up_make_canvas(self):
        def put_ana_histo_name(grps):
            for grp in grps:
                grp.name = grp.renderers[0].in_file_path.replace('/', '_')
                yield grp

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
        bldr = put_ana_histo_name(bldr)
        bldr = decorate(bldr)
        if self.hook_canvas_pre_build:
            bldr = self.hook_canvas_pre_build(bldr)
        bldr = run_build_procedure(bldr)
        if self.hook_canvas_post_build:
            bldr = self.hook_canvas_post_build(bldr)
        self.stream_canvas = gen.build_canvas(bldr)

    def set_up_save_canvas(self):
        if self.save_lin_log_scale:
            self.stream_canvas = gen.save_canvas_lin_log(
                self.stream_canvas,
                self.save_name_func,
            )
        else:
            if self.save_log_scale:
                self.stream_canvas = gen.switch_log_scale(self.stream_canvas)
            self.stream_canvas = gen.save(
                self.stream_canvas,
                self.save_name_func,
            )

    def run_sequence(self):
        count = gen.consume_n_count(self.stream_canvas)
        level = "INFO " if count else "WARNING "
        message = level+self.name+" produced "+str(count)+" canvases."
        self.message(message)

    def run(self):
        self.configure()
        self.load_content()
        self.set_up_content()
        self.store_content_as_result()
        self.set_up_make_canvas()
        self.set_up_save_canvas()
        self.run_sequence()


def _mk_legendnames(filenames):
    # only one file: return directly
    if len(filenames) < 2:
        return filenames[:]

    # try the sframe way:
    lns = list(n.split('.') for n in filenames)
    if all(len(l) == 5 for l in lns):
        return list(l[3] for l in lns)

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
        return filenames[:]
    return lns


class RootFilePlotter(toolinterface.ToolChain):
    """
    Plots all histograms in a rootfile.

    **NOTE: please use the** ``tools.mk_rootfile_plotter`` **function!**

    :param rootfile:            str, search pattern for rootfiles
    :param plotter_factory:     factory function for RootFilePlotter
                                default: ``None``
    :param flat:                bool, flatten the rootfile structure
                                default: ``False``
    :param name:                str, tool name
    """

    def __init__(self,
                 rootfile,
                 plotter_factory=None,
                 flat=False,
                 name=None,
                 filter_keyfunc=None):
        super(RootFilePlotter, self).__init__(name)

        self.private_plotter = None
        self.rootfile = rootfile  # only the base instance has this
        if not rootfile:
            return
        rootfiles = glob.glob(rootfile)
        if not rootfiles:
            return

        self.message('INFO Setting up RootFilePlotter')

        # setup aliases
        ROOT.gROOT.SetBatch()
        if not plotter_factory:
            plotter_factory = Plotter
        aliases = diskio.generate_aliases(self.rootfile)
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

        legendnames = _mk_legendnames(rootfiles)
        legendnames = dict(itertools.izip(rootfiles, legendnames))
        self.message(
            'INFO Here are the rootfiles and legend names that I will use:\n'
            + '\n'.join('%22s: %s' % (v,k) for k,v in legendnames.iteritems())
        )
        colors = settings.default_colors[:len(rootfiles)]
        def colorizer(wrps):
            wrps = gen.apply_linecolor(wrps, colors)
            wrps = gen.apply_markercolor(wrps, colors)
            for w in wrps:
                if not w.legend:
                    w.legend = legendnames[os.path.basename(w.file_path)]
                yield w

        # either print all in one dir...
        if flat:
            self.private_plotter = plotter_factory(
                filter_keyfunc=lambda _: True,
                load_func=lambda _: colorizer(gen.load(gen.fs_content())),
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

                # make dirs if not in basedir
                if len(path) > 1:
                    for folder in path[:-1]:
                        if not folder in rfp.tool_names:
                            rfp.add_tool(RootFilePlotter(
                                None, plotter_factory, name=folder))
                        rfp = rfp.tool_names[folder]

                # make plotter instance if not done already
                if not rfp.private_plotter:
                    def _mk_loader(p):
                        # This function creates a separate namespace for p
                        def loader(filter_keyfunc):
                            wrps = analysis.fs_aliases
                            wrps = itertools.ifilter(
                                lambda w: w.in_file_path.split('/')[:-1] == p
                                          and filter_keyfunc(w),
                                wrps
                            )
                            wrps = gen.load(wrps)
                            wrps = colorizer(wrps)
                            return wrps
                        return loader

                    rfp.private_plotter = plotter_factory(
                        filter_keyfunc=lambda _: True,
                        plot_grouper=plot_grouper_by_in_file_path,
                        save_name_func=lambda w: w._renderers[0].name,
                        load_func=_mk_loader(path[:-1]),
                        canvas_decorators=[rendering.Legend],
                    )

    def run(self):
        time.sleep(1)  # weird bug in root...
        old_aliases = analysis.fs_aliases
        if self.rootfile:
            analysis.fs_aliases = self.aliases
        super(RootFilePlotter, self).run()
        if self.private_plotter:
            self.private_plotter.run()
        if self.rootfile:
            analysis.fs_aliases = old_aliases
