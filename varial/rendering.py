"""
From histogram data to graphical plots.

The members of this package make plots from histograms or other wrapped
ROOT-objects. The 'Renderers' extend the functionality of wrappers for drawing.
The ROOT-canvas is build with the ``CanvasBuilder`` class.

Decorators can be used for customization of a ``CanvasBuilder`` instance.
They provide ways to add content to canvases, like a legend, boxes, lines,
text, etc.. See :ref:`util-module` for details on the decorator
implementation. Apply as below (e.g. with a 'Legend' or a 'TextBox'
Decorator)::

    cb = CanvasBuilder(wrappers)
    cb = Legend(cb, x1=0.2, x2=0.5)             # wrap cb with Legend
    cb = Textbox(cb, text="Some boxed Text")    # wrap Legend with Textbox
    canvas_wrp = cb.build_canvas()
"""


################################################################# renderers ###
import collections
import ROOT
import wrappers


class Renderer(object):
    """
    Baseclass for rendered wrappers.
    """
    def __init__(self, wrp):
        self.val_x_min = 0.
        self.val_x_max = 0.
        self.val_y_min = 0.
        self.val_y_max = 0.
        self.__dict__.update(wrp.__dict__)

    def x_min(self):
        return self.val_x_min

    def x_max(self):
        return self.val_x_max

    def y_min(self):
        return self.val_y_min

    def y_max(self):
        return self.val_y_max

    def y_min_gr_zero(self):
        return self.y_min()

    def draw(self, option=''):
        pass


class HistoRenderer(Renderer, wrappers.HistoWrapper):
    """
    Extend HistoWrapper for drawing.
    """
    def __init__(self, wrp):
        super(HistoRenderer, self).__init__(wrp)
        if hasattr(wrp, 'draw_option'):
            self.draw_option = wrp.draw_option
        elif 'TH2' in wrp.type:
            self.draw_option = 'colz'
        elif self.is_data:
            self.draw_option = 'E1X0'
        else:
            self.draw_option = 'hist'

    def x_min(self):
        return self.val_x_min or self.histo.GetXaxis().GetXmin()

    def x_max(self):
        return self.val_x_max or self.histo.GetXaxis().GetXmax()

    def y_min(self):
        return self.val_y_min or self.histo.GetMinimum() + 1e-23  # > 0 cuts away half numbers

    def y_max(self):
        return self.val_y_max or self.histo.GetMaximum()

    def y_min_gr_zero(self, histo=None):
        if not histo:
            histo = self.histo
        nbins = histo.GetNbinsX()
        min_val = histo.GetMinimum()  # min on y axis
        if min_val < 1e-23 < histo.GetMaximum():  # should be greater than zero
            try:
                min_val = min(
                    histo.GetBinContent(i)
                    for i in xrange(nbins + 1)
                    if histo.GetBinContent(i) > 1e-23
                )
            except ValueError:
                min_val = 1e-23
        return min_val

    def draw(self, option=''):
        self.histo.Draw(self.draw_option + option)


class StackRenderer(HistoRenderer, wrappers.StackWrapper):
    """
    Extend StackWrapper for drawing.
    """
    def __init__(self, wrp):
        super(StackRenderer, self).__init__(wrp)
        # prepare the sum histo
        self.histo.SetFillColor(922)
        self.histo.SetMarkerColor(1)
        self.histo.SetMarkerSize(0)
        self.histo.SetFillStyle(3008)
        self.histo.SetLineColor(1)
        self.histo.SetTitle('Stat. uncert. MC')
        self.draw_option_sum = 'sameE2'

    def y_min_gr_zero(self, histo=None):
        return super(StackRenderer, self).y_min_gr_zero(
            self.stack.GetHists()[0]
        )

    def draw(self, option=''):
        self.stack.Draw(self.draw_option + option)
        self.stack.GetXaxis().SetTitle(self.histo.GetXaxis().GetTitle())
        self.stack.GetYaxis().SetTitle(self.histo.GetYaxis().GetTitle())
        self.histo.Draw(self.draw_option_sum)


class GraphRenderer(Renderer, wrappers.GraphWrapper):
    """
    Extend GraphWrapper for drawing.
    """
    def __init__(self, wrp):
        super(GraphRenderer, self).__init__(wrp)
        if hasattr(wrp, 'draw_option'):
            self.draw_option = wrp.draw_option
        else:
            self.draw_option = 'P'

    def x_min(self):
        return self.val_x_min or self.graph.GetXaxis().GetXmin()

    def x_max(self):
        return self.val_x_max or self.graph.GetXaxis().GetXmax()

    def y_min(self):
        return self.val_y_min or self.graph.GetYaxis().GetXmin() + 1e-23  # > 0 cuts away half numbers

    def y_max(self):
        return self.val_y_max or self.graph.GetYaxis().GetXmax()

    def draw(self, option=''):
        if 'same' in option:
            option.replace('same', '')
        else:
            option += 'A'
        self.graph.Draw(self.draw_option + option)


############################################################ canvas-builder ###
import settings
import history
from ROOT import TCanvas, TObject


def _renderize(wrp):
    if isinstance(wrp, Renderer):
        return wrp
    if isinstance(wrp, wrappers.GraphWrapper):
        return GraphRenderer(wrp)
    if isinstance(wrp, wrappers.StackWrapper):
        return StackRenderer(wrp)
    if isinstance(wrp, wrappers.HistoWrapper):
        return HistoRenderer(wrp)


def _renderize_iter(wrps):
    rnds = []
    for wrp in wrps:
        rnds.append(_renderize(wrp))
    return rnds


class CanvasBuilder(object):
    """
    Create a TCanvas and plot wrapped ROOT-objects.

    Use this class like so::

        cb = CanvasBuilder(list_of_wrappers, **kws)
        canvas_wrp = cb.build_canvas()

    * ``list_of_wrappers`` is can also be a list of renderers. If not, the
      renderers are created automatically.

    * ``**kws`` can be empty. Accepted keywords are ``name=`` and ``title=`` and
      any keyword that is accepted by ``histotools.wrappers.CanvasWrapper``.

    When designing decorators, these instance data members can be of interest:

    ================= =========================================================
    ``x_bounds``      Bounds of canvas area in x
    ``y_bounds``      Bounds of canvas area in y
    ``y_min_gr_zero`` smallest y greater zero (need in log plotting)
    ``canvas``        Reference to the TCanvas instance
    ``main_pad``      Reference to TPad instance
    ``second_pad``    Reference to TPad instance or None
    ``first_drawn``   TObject which is first drawn (for valid TAxis reference)
    ``legend``        Reference to TLegend object.
    ================= =========================================================
    """
    class TooManyStacksError(Exception): pass
    class NoInputError(Exception): pass

    x_bounds       = 0., 0.
    y_bounds       = 0., 0.
    y_min_gr_zero  = 0.
    canvas         = None
    main_pad       = None
    second_pad     = None
    first_drawn    = None
    legend         = None

    def __init__(self, wrps, **kws):
        if not isinstance(wrps, collections.Iterable):
            raise self.NoInputError('CanvasBuilder wants iterable of wrps!')
        super(CanvasBuilder, self).__init__()
        self.kws = kws

        # only one stack, which should be one first place
        wrps = sorted(
            wrps,
            key=lambda r: not isinstance(r, wrappers.StackWrapper)
        )
        if len(wrps) > 1 and isinstance(wrps[1], wrappers.StackWrapper):
            raise self.TooManyStacksError(
                'CanvasWrapper takes at most one StackWrapper'
            )

        # for stacks and overlays
        if len(wrps) > 1:
            if isinstance(wrps[0], wrappers.StackWrapper):
                if not hasattr(wrps[0], 'draw_option'):
                    wrps[0].draw_option = 'hist'
                for w in wrps[1:]:
                    if not hasattr(w, 'draw_option'):
                        if w.is_signal:
                            w.draw_option = 'hist'
                            w.histo.SetLineWidth(2)
                        elif not w.is_data:  # circles for pseudo-data
                            w.draw_option = 'E1X0'
                            w.draw_option_legend = 'p'
                            w.histo.SetMarkerStyle(4)

        # instanciate Renderers
        rnds = list(_renderize_iter(wrps))
        self.renderers = rnds

        # name, title in_file_path
        self.name = kws.get('name', rnds[0].name)
        self.title = kws.get('title', rnds[0].title)
        self.in_file_path = kws.get('in_file_path', rnds[0].in_file_path)

    def __del__(self):
        """Remove the pads first."""
        if self.main_pad:
            self.main_pad.Delete()
        if self.second_pad:
            self.second_pad.Delete()

    def configure(self):
        pass

    def find_x_y_bounds(self):
        """Scan ROOT-objects for x and y bounds."""
        rnds = self.renderers
        x_min = min(r.x_min() for r in rnds)
        x_max = max(r.x_max() for r in rnds)
        self.x_bounds = x_min, x_max
        y_min = min(r.y_min() for r in rnds)
        y_max = max(r.y_max() for r in rnds)
        self.y_bounds = y_min, y_max
        self.y_min_gr_zero = min(r.y_min_gr_zero() for r in rnds)

    def make_empty_canvas(self):
        """Instanciate ``self.canvas`` ."""
        self.canvas = TCanvas(
            self.name,
            self.title,
            settings.canvas_size_x,
            settings.canvas_size_y,
        )
        self.main_pad = self.canvas

    def draw_full_plot(self):
        """The renderers draw method is called."""
        for i, rnd in enumerate(self.renderers):
            if not i:
                self.first_drawn = rnd.primary_object()
                self.first_drawn.SetTitle('')
                rnd.draw('')
            else:
                rnd.draw('same')

    def do_final_cosmetics(self):
        """Pimp the canvas!"""
        y_min, y_max = self.y_bounds
        self.first_drawn.GetXaxis().SetNoExponent()
        self.first_drawn.GetXaxis().SetLabelSize(0.052)
        self.first_drawn.SetMinimum(y_max / 10000.)
        self.first_drawn.SetMaximum(y_max * 1.1)

    def run_procedure(self):
        """
        This method calls all other methods, which fill and build the canvas.
        """
        self.configure()
        self.find_x_y_bounds()
        self.make_empty_canvas()
        self.draw_full_plot()
        self.do_final_cosmetics()

    def _track_canvas_history(self):
        list_of_histories = []
        for rnd in self.renderers:
            list_of_histories.append(rnd.history)
        hstry = history.History('CanvasBuilder')
        hstry.add_args(list_of_histories)
        hstry.add_kws(self.kws)
        return hstry

    def _del_builder_refs(self):
        for k,obj in self.__dict__.items():
            if isinstance(obj, TObject):
                setattr(self, k, None)

    def build_canvas(self):
        """
        With this method, the building procedure is started.

        :return: ``CanvasWrapper`` instance.
        """
        if not self.canvas:
            self.run_procedure()
        canvas = self.canvas
        canvas.Modified()
        canvas.Update()
        wrp = wrappers.CanvasWrapper(
            canvas,
            main_pad    = self.main_pad,
            second_pad  = self.second_pad,
            legend      = self.legend,
            first_drawn = self.first_drawn,
            x_bounds    = self.x_bounds,
            y_bounds    = self.y_bounds,
            y_min_gr_0  = self.y_min_gr_zero,
            history     = self._track_canvas_history(),
            _renderers   = self.renderers,
            **self.kws
        )
        self._del_builder_refs()
        self.canvas_wrp = wrp
        return wrp


############################################# customization with decorators ###
import util
import operations as op
from ROOT import TLegend, TPad, TPaveText


class TitleBox(util.Decorator):
    """
    Draws title-box with TPaveText above canvas window.

    Instanciate with text argument:
    ``tb = TitleBox(None, text='My funny title')``.
    """
    def do_final_cosmetics(self):
        self.decoratee.do_final_cosmetics()

        titlebox = TPaveText(0.28, 0.94, 0.9, 0.97, 'brNDC')
        titlebox.AddText(self.dec_par.get('text', 'ENTER TEXT FOR TITLEBOX!'))
        titlebox.SetTextSize(0.042)
        titlebox.SetFillStyle(0)
        titlebox.SetBorderSize(0)
        titlebox.SetTextAlign(13)
        titlebox.SetMargin(0.0)
        titlebox.SetFillColor(0)
        titlebox.Draw('SAME')
        self.titlebox = titlebox


class TextBox(util.Decorator):
    """Draw Textboxes individually by renderer name"""
    def __init__(self, inner, dd=True, **kws):
        super(TextBox, self).__init__(inner, dd, **kws)
        self.dec_par.update(kws)
        assert('textbox_dict' in self.dec_par)

    def do_final_cosmetics(self):
        self.decoratee.do_final_cosmetics()
        textbox = self.dec_par['textbox_dict'][self.renderers[0].name]
        textbox.Draw()


class Legend(util.Decorator):
    """
    Adds a legend to the main_pad.

    Takes entries from ``self.main_pad.BuildLegend()`` .
    The box height is adjusted by the number of legend entries.
    No border or shadow are printed. See __init__ for keywords.
    """
    def __init__(self, inner, dd='True', **kws):
        super(Legend, self).__init__(inner, dd)
        self.dec_par.update(settings.defaults_Legend)
        self.dec_par.update(kws)

    def make_entry_tupels(self, legend):
        rnds = self.renderers
        entries = []
        for entry in legend.GetListOfPrimitives():
            obj = entry.GetObject()
            label = entry.GetLabel()
            is_data = ('Data' in label) or ('data' in label)
            draw_opt = self.dec_par['opt']
            if is_data:
                draw_opt = self.dec_par['opt_data']
            for rnd in rnds:
                if isinstance(rnd, StackRenderer):
                    continue
                if rnd.primary_object() is obj:
                    if hasattr(rnd, 'legend'):
                        label = rnd.legend
                    if hasattr(rnd, 'draw_option_legend'):
                        draw_opt = rnd.draw_option_legend
                    break
            entries.append((obj, label, draw_opt))
        return entries

    def _calc_bounds(self, n_entries):
        par = self.dec_par
        x_pos   = par['x_pos']
        y_pos   = par['y_pos']
        width   = par['label_width']
        height  = par['label_height'] * n_entries
        x_pos *= (1. - width)  # adjust for space left
        y_pos *= (1. - height) # adjust for space left
        return x_pos, y_pos, x_pos + width, y_pos + height

    def do_final_cosmetics(self):
        """
        Only ``do_final_cosmetics`` is overwritten here.

        If self.legend == None, this method will create a default legend and
        store it to self.legend
        """
        if self.legend:
            return

        tmp_leg = self.main_pad.BuildLegend(0.1, 0.6, 0.5, 0.8) # get legend entry objects
        entries = self.make_entry_tupels(tmp_leg)
        tmp_leg.Clear()
        self.main_pad.GetListOfPrimitives().Remove(tmp_leg)
        tmp_leg.Delete()

        bounds = self._calc_bounds(len(entries))
        legend = TLegend(*bounds)
        legend.SetBorderSize(0)
        legend.SetTextSize(settings.box_text_size)
        par = self.dec_par
        if par['reverse']:
            entries.reverse()
        for obj, label, draw_opt in entries:
            legend.AddEntry(obj, label, draw_opt)
        legend.Draw()
        self.legend = legend
        self.decoratee.do_final_cosmetics()         # Call next inner class!!


class BottomPlot(util.Decorator):
    """Base class for all plot business at the bottom of the canvas."""
    def __init__(self, inner, dd = True, **kws):
        super(BottomPlot, self).__init__(inner, dd, **kws)
        self.dec_par.update(settings.defaults_BottomPlot)
        self.dec_par.update(kws)

    def configure(self):
        self.decoratee.configure()
        self.__dict__['no_second_histo'] = len(self.renderers) < 2

    def define_bottom_hist(self):
        """Overwrite this method and give a histo-ref to self.bottom_hist."""
        pass

    def make_empty_canvas(self):
        """Instanciate canvas with two pads."""
        # canvas
        self.decoratee.make_empty_canvas()
        if self.no_second_histo:
            return
        name = self.name
        self.main_pad = TPad(
            'main_pad_' + name,
            'main_pad_' + name,
            0, 0.25, 1, 1
        )
        # main (upper) pad
        main_pad = self.main_pad
        main_pad.SetTopMargin(0.1)
        main_pad.SetBottomMargin(0.)
        main_pad.SetRightMargin(0.04)
        main_pad.SetLeftMargin(0.16)
        main_pad.Draw()
        # bottom pad
        self.canvas.cd()
        self.second_pad = TPad(
            'bottom_pad_' + name,
            'bottom_pad_' + name,
            0, 0, 1, 0.25
        )
        second_pad = self.second_pad
        second_pad.SetTopMargin(0.)
        second_pad.SetBottomMargin(0.375)
        second_pad.SetRightMargin(0.04)
        second_pad.SetLeftMargin(0.16)
        second_pad.SetGridy()
        second_pad.Draw()

    def draw_full_plot(self):
        """Make bottom plot, draw both."""
        # draw main histogram
        self.main_pad.cd()
        self.decoratee.draw_full_plot()
        if self.no_second_histo:
            return
        first_drawn = self.first_drawn
        first_drawn.GetYaxis().CenterTitle(1)
        first_drawn.GetYaxis().SetTitleSize(0.055)
        first_drawn.GetYaxis().SetTitleOffset(1.3)
        first_drawn.GetYaxis().SetLabelSize(0.055)
        first_drawn.GetXaxis().SetNdivisions(505)
        # make bottom histo and draw it
        self.second_pad.cd()
        self.define_bottom_hist()
        bottom_hist = self.bottom_hist

        bottom_hist.GetYaxis().CenterTitle(1)
        bottom_hist.GetYaxis().SetTitleSize(0.15) #0.11
        bottom_hist.GetYaxis().SetTitleOffset(0.44) #0.55
        bottom_hist.GetYaxis().SetLabelSize(0.16)
        bottom_hist.GetYaxis().SetNdivisions(205)

        bottom_hist.GetXaxis().SetNoExponent()
        bottom_hist.GetXaxis().SetTitleSize(0.16)
        bottom_hist.GetXaxis().SetLabelSize(0.17)
        bottom_hist.GetXaxis().SetTitleOffset(1)
        bottom_hist.GetXaxis().SetLabelOffset(0.006)
        bottom_hist.GetXaxis().SetNdivisions(505)
        bottom_hist.GetXaxis().SetTickLength(
            bottom_hist.GetXaxis().GetTickLength() * 3.
        )

        bottom_hist.SetTitle('')
        bottom_hist.SetLineColor(1)
        bottom_hist.SetLineStyle(1)
#        y_min = self.dec_par['y_min']
#        y_max = self.dec_par['y_max']
#        hist_min = bottom_hist.GetMinimum()
#        hist_max = bottom_hist.GetMaximum()
#        if y_min < hist_min:
#            y_min = hist_min
#        if y_max > hist_max:
#            y_max = hist_max
#        bottom_hist.GetYaxis().SetRangeUser(y_min, y_max)
        bottom_hist.Draw(self.dec_par['draw_opt'])
        if bottom_hist.GetMinimum() < self.dec_par['x_min']:
            bottom_hist.GetYaxis().SetRangeUser(
                self.dec_par['x_min'],
                bottom_hist.GetMaximum()
            )
        if self.bottom_hist.GetMaximum() > self.dec_par['x_max']:
            self.bottom_hist.GetYaxis().SetRangeUser(
                bottom_hist.GetMinimum(),
                self.dec_par['x_max']
            )

        # set focus on main_pad for further drawing
        self.main_pad.cd()


class BottomPlotRatio(BottomPlot):
    """Ratio of first and second histogram in canvas."""
    def define_bottom_hist(self):
        rnds = self.renderers
        wrp = op.div(iter(rnds))
        for i in xrange(1, wrp.histo.GetNbins() + 1):
            cont = wrp.histo.GetBinContent(i)
            wrp.histo.SetBinContent(i, cont - 1.)
        wrp.histo.SetYTitle(self.dec_par['y_title'])
        self.bottom_hist = wrp.histo


class BottomPlotRatioSplitErr(BottomPlot):
    """Same as BottomPlotRatio, but split MC and data uncertainties."""
    def define_bottom_hist(self):
        rnds = self.renderers
        mc_histo = rnds[0].histo.Clone()
        da_histo = rnds[1].histo.Clone()
        div_hist = da_histo.Clone()
        div_hist.Divide(mc_histo)
        for i in xrange(1, mc_histo.GetNbinsX() + 1):
            mc_val  = mc_histo.GetBinContent(i)
            mc_err  = mc_histo.GetBinError(i)
            da_val  = da_histo.GetBinContent(i)
            da_err  = da_histo.GetBinError(i)
            div_val = div_hist.GetBinContent(i)
            mc_histo.SetBinContent(i, 0.)
            if mc_val > 1e-37:
                mc_histo.SetBinError(i, mc_err / mc_val)
                div_hist.SetBinContent(i, div_val - 1.)
            else:
                mc_histo.SetBinError(i, 0.)
            if da_val > 1e-37:
                div_hist.SetBinError(i, da_err * div_val / da_val)
        div_hist.SetYTitle(self.dec_par['y_title'])
        div_hist.SetMarkerSize(0)
        mc_histo.SetYTitle(self.dec_par['y_title'])
        mc_histo.SetFillColor(921)
        mc_histo.SetMarkerColor(1)
        mc_histo.SetMarkerSize(0)
        mc_histo.SetFillStyle(3008)
        mc_histo.SetLineColor(1)
        self.bottom_hist = div_hist
        self.bottom_hist_mc_err = mc_histo

    def draw_full_plot(self):
        """Draw mc error histo underneat data ratio."""
        super(BottomPlotRatioSplitErr, self).draw_full_plot()
        if self.no_second_histo:
            return
        self.second_pad.cd()
        self.bottom_hist_mc_err.Draw('sameE2')
        self.bottom_hist.Draw(self.dec_par['draw_opt'] + 'same')
        self.main_pad.cd()


# TODO use WrapperWrapper
