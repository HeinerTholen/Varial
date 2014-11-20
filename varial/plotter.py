import itertools
import ROOT

import generators as gen
import rendering
import toolinterface


_group_th2d_iter = iter(xrange(9999))
def plot_grouper(wrps):
    # enumerate th2d wrappers, so they get their own groups
    return gen.group(wrps, key_func=lambda w: w.analyzer+"_"+w.name+(
        "%03d" % next(_group_th2d_iter)
        if isinstance(w.histo, ROOT.TH2D)
        else ""
    ))


def overlay_colorizer(wrps, colors=None):
    wrps = gen.apply_histo_linecolor(wrps, colors)
    for w in wrps:
        w.histo.SetFillStyle(0)
        yield w


class FSPlotter(toolinterface.Tool):
    """
    A plotter. Makes stacks and overlays data by default.

    Overriding set_up_content and setting self.stream_content lets
    Default attributes, that can be overwritten by init keywords:

    >>> defaults = {
    ...    'input_result_path': None,
    ...    'filter_keyfunc': None,
    ...    'hook_loaded_histos': None,
    ...    'plot_grouper': plot_grouper,
    ...    'plot_setup': lambda w: gen.mc_stack_n_data_sum(w, None, True),
    ...    'hook_canvas_pre_build': None,
    ...    'hook_canvas_post_build': None,
    ...    'save_log_scale': False,
    ...    'save_lin_log_scale': False,
    ...    'keep_content_as_result': False,
    ...    'canvas_decorators': [
    ...        rendering.BottomPlotRatioSplitErr,
    ...        rendering.Legend
    ...    ]
    ...}
    """
    defaults_attrs = {
        'input_result_path': None,
        'filter_keyfunc': None,
        'hook_loaded_histos': None,
        'plot_grouper': plot_grouper,
        'plot_setup': lambda w: gen.mc_stack_n_data_sum(w, None, True),
        'hook_canvas_pre_build': None,
        'hook_canvas_post_build': None,
        'save_log_scale': False,
        'save_lin_log_scale': False,
        'keep_content_as_result': False,
        'save_name_lambda': lambda wrp: wrp.name,
        'canvas_decorators': [
            rendering.BottomPlotRatioSplitErr,
            rendering.Legend
        ]
    }

    class NoFilterDictError(Exception):
        pass

    def __init__(self, name=None, **kws):
        super(FSPlotter, self).__init__(name)
        defaults = dict(self.defaults_attrs)
        defaults.update(self.__dict__)  # do not overwrite user stuff
        defaults.update(kws)            # add keywords
        self.__dict__.update(defaults)  # set attributes in place
        self.stream_content = None
        self.stream_canvas = None

    def configure(self):
        pass

    def load_content(self):
        if self.input_result_path:
            wrps = self.lookup(self.input_result_path)
            if not wrps:
                raise RuntimeError(
                    'ERROR Input not found: "%s"' % self.input_result_path)
        else:
            wrps = self.lookup('../FSHistoLoader')
        if wrps:
            if self.filter_keyfunc:
                wrps = itertools.ifilter(self.filter_keyfunc, wrps)
        else:
            if not self.filter_keyfunc:
                self.message("WARNING No filter_keyfunc set! "
                             "Working with _all_ histograms.")
            wrps = gen.fs_filter_active_sort_load(self.filter_keyfunc)
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
                grp.name = grp.renderers[0].analyzer+"_"+grp.name
                yield grp

        def run_build_procedure(bldr):
            for b in bldr:
                b.run_procedure()
                yield b

        def decorate(bldr):
            for b in bldr:
                if not isinstance(b.renderers[0].histo, ROOT.TH2D):
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
                self.save_name_lambda,
            )
        else:
            if self.save_log_scale:
                self.stream_canvas = gen.switch_log_scale(self.stream_canvas)
            self.stream_canvas = gen.save(
                self.stream_canvas,
                self.save_name_lambda,
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
