# rendering.py

################################################################# renderers ###
import collections
import wrappers

class Renderer(object):
    """
    Baseclass for rendered wrappers.
    """
    def __init__(self, wrp):
        self.__dict__.update(wrp.__dict__)

    def x_min(self): pass

    def x_max(self): pass

    def y_min(self): pass

    def y_max(self): pass

    def y_min_gr_zero(self): return self.y_min()

    def draw(self, option=""): pass


class HistoRenderer(Renderer, wrappers.HistoWrapper):
    """
    Extend HistoWrapper for drawing.
    """
    def __init__(self, wrp):
        super(HistoRenderer, self).__init__(wrp)
        if self.is_data:
            self.draw_option = "E1X0"
        else:
            self.draw_option = "hist"

    def x_min(self):
        return self.histo.GetXaxis().GetXmin()

    def x_max(self):
        return self.histo.GetXaxis().GetXmax()

    def y_min(self):
        return self.histo.GetMinimum()

    def y_max(self):
        return self.histo.GetMaximum()

    def y_min_gr_zero(self, histo=None):
        if not histo: histo = self.histo
        nbins = histo.GetNbinsX()
        min_val = histo.GetMinimum() # min on y axis
        if min_val < 1e-23 < histo.GetMaximum(): # should be greater than zero
            min_val = min(
                histo.GetBinContent(i)
                    for i in xrange(nbins + 1)
                    if histo.GetBinContent(i) > 1e-23
            )
        return min_val

    def draw(self, option=""):
        self.histo.Draw(self.draw_option + option)


class StackRenderer(HistoRenderer, wrappers.StackWrapper):
    """
    Extend StackWrapper for drawing.
    """
    def __init__(self, wrp):
        super(StackRenderer, self).__init__(wrp)
        # prepare the sum histo
        self.histo.SetFillColor(1)
        self.histo.SetMarkerColor(1)
        self.histo.SetMarkerSize(0)
        self.histo.SetFillStyle(3005)
        self.histo.SetLineColor(1)
        self.histo.SetTitle("stat. uncert. MC")
        self.draw_option_sum = "sameE2"

    def y_min_gr_zero(self, histo=None):
        return super(StackRenderer, self).y_min_gr_zero(
            self.stack.GetHists()[0]
        )

    def draw(self, option=""):
        self.stack.Draw(self.draw_option + option)
        self.stack.GetXaxis().SetTitle(self.histo.GetXaxis().GetTitle())
        self.stack.GetYaxis().SetTitle(self.histo.GetYaxis().GetTitle())
        self.histo.Draw(self.draw_option_sum)

############################################################ canvas-builder ###
import settings
import history
from ROOT import TCanvas, TObject

def _renderize(wrp): #TODO maybe use reflection here??
    if isinstance(wrp, Renderer):
        return wrp
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
            raise self.NoInputError("CanvasBuilder wants iterable of wrps!")
        super(CanvasBuilder, self).__init__()
        self.kws            = kws

        # only one stack, which should be one first place
        rnds = _renderize_iter(wrps)
        rnds = sorted(
            rnds,
            key=lambda r: not isinstance(r, StackRenderer)
        )
        for i, rnd in enumerate(rnds):
            if i and isinstance(rnd, StackRenderer):
                raise self.TooManyStacksError(
                    "CanvasWrapper takes at most one stack"
                )
        self.renderers = rnds

        # if no name is specified, just take first rnds
        self.name  = kws.get("name", rnds[0].name)
        self.title = kws.get("title", rnds[0].title)

    def __del__(self):
        """Remove the pads first."""
        if self.second_pad:
            self.main_pad.Delete()
            self.main_pad.Delete()

    def configure(self):
        """Called at first. Can be used to initialize decorators."""

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
                self.first_drawn.SetTitle("")
                rnd.draw("")
            else:
                rnd.draw("same")

    def do_final_cosmetics(self):
        """Pimp the canvas!"""
        y_min, y_max = self.y_bounds
        self.first_drawn.GetXaxis().SetNoExponent()
        self.first_drawn.GetXaxis().SetLabelSize(0.052)
        #self.first_drawn.SetMinimum(y_min * 0.9)
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
        hstry = history.History("CanvasBuilder")
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
            **self.kws
        )
        self._del_builder_refs()
        return wrp

    #TODO: Think about making CanvasWrapper and CanvasBuilder one object

############################################# customization with decorators ###
import decorator as dec
import operations as op
from ROOT import TLegend, TPad, TPaveText

class Legend(dec.Decorator):
    """
    Adds a legend to the main_pad.

    Takes entries from ``self.main_pad.BuildLegend()`` .
    The box height is adjusted by the number of legend entries.
    No border or shadow are printed. See __init__ for keywords.
    """
    def __init__(self, inner, dd = "True", **kws):
        super(Legend, self).__init__(inner, dd)
        self.dec_par["x1"]          = 0.43
        self.dec_par["x2"]          = 0.67
        self.dec_par["y2"]          = 0.88
        self.dec_par["y_shift"]     = 0.04
        self.dec_par["opt"]         = "f"
        self.dec_par["opt_data"]    = "p"
        self.dec_par["reverse"]     = True
        self.dec_par.update(kws)

    def make_entry_tupels(self, legend):
        rnds = self.renderers
        entries = []
        for entry in legend.GetListOfPrimitives():
            obj = entry.GetObject()
            label = entry.GetLabel()
            is_data = ("Data" in label) or ("data" in label)
            for rnd in rnds:
                if isinstance(rnd, StackRenderer): continue
                if rnd.primary_object() is obj:
                    is_data = rnd.is_data
                    if hasattr(rnd, "legend"):
                        label = rnd.legend
                    break
            entries.append((obj, label, is_data))
        return entries

    def do_final_cosmetics(self):
        """
        Only ``do_final_cosmetics`` is overwritten here.

        If self.legend == None, this method will create a default legend and
        store it to self.legend
        """
        if self.legend: return

        tmp_leg = self.main_pad.BuildLegend(0.1, 0.6, 0.5, 0.8) # get legend entry objects
        entries = self.make_entry_tupels(tmp_leg)
        tmp_leg.Clear()
        self.main_pad.GetListOfPrimitives().Remove(tmp_leg)
        tmp_leg.Delete()

        par = self.dec_par
        x1, x2, y2, y_shift = par["x1"], par["x2"], par["y2"], par["y_shift"]
        y1 = y2 - (len(entries) * y_shift)
        legend = TLegend(x1, y1, x2, y2)
        legend.SetBorderSize(0)
        if par["reverse"]:
            entries.reverse()
        for obj, label, is_data in entries:
            if is_data:
                legend.AddEntry(obj, label, par["opt_data"])
            else:
                legend.AddEntry(obj, label, par["opt"])
        legend.Draw()
        self.legend = legend
        self.decoratee.do_final_cosmetics()         # Call next inner class!!


class LegendLeft(Legend):
    """Just as Legend, but plotted on the left."""
    def __init__(self, inner, dd = "True", **kws):
        kws["x1"] = 0.19
        kws["x2"] = 0.43
        super(LegendLeft, self).__init__(inner, dd, **kws)


class LegendRight(Legend):
    """Just as Legend, but plotted on the right."""
    def __init__(self, inner, dd = "True", **kws):
        kws["x1"] = 0.67
        kws["x2"] = 0.88
        super(LegendRight, self).__init__(inner, dd, **kws)


class BottomPlot(dec.Decorator):
    """Base class for all plot business at the bottom of the canvas."""
    def __init__(self, inner, dd = "True", **kws):
        super(BottomPlot, self).__init__(inner, dd, **kws)
        self.dec_par["draw_opt"] = kws.get("draw_opt", "E1")

    def define_bottom_hist(self):
        """Overwrite this method and give a histo-ref to self.bottom_hist."""
        pass

    def make_empty_canvas(self):
        """Instanciate canvas with two pads."""
        # canvas
        self.decoratee.make_empty_canvas()
        name = self.name
        self.main_pad = TPad(
            "main_pad_" + name, 
            "main_pad_" + name, 
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
            "bottom_pad_" + name, 
            "bottom_pad_" + name, 
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
        bottom_hist.GetYaxis().SetTitleSize(0.165) #0.11
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

        bottom_hist.SetTitle("")
        bottom_hist.SetYTitle("Ratio")
        bottom_hist.SetLineColor(1)
        bottom_hist.SetLineStyle(1)
#        y_min = self.dec_par["y_min"]
#        y_max = self.dec_par["y_max"]
#        hist_min = bottom_hist.GetMinimum()
#        hist_max = bottom_hist.GetMaximum()
#        if y_min < hist_min:
#            y_min = hist_min
#        if y_max > hist_max:
#            y_max = hist_max
#        bottom_hist.GetYaxis().SetRangeUser(y_min, y_max)
        bottom_hist.Draw(self.dec_par["draw_opt"])

        # set focus on main_pad for further drawing
        self.main_pad.cd()


class BottomPlotRatio(BottomPlot):
    """Ratio of first and second histogram in canvas."""
    def define_bottom_hist(self):
        rnds = self.renderers
        assert(len(rnds) > 1)
        wrp = op.div(iter(rnds))
        wrp.histo.SetYTitle("Data/MC")
        self.bottom_hist = wrp.histo
        #TODO: use HistoRenderer here

    def draw_full_plot(self):
        """Fix scale of ratio y axis."""
        super(BottomPlotRatio, self).draw_full_plot()
        if self.bottom_hist.GetMaximum() > 5.:
            self.bottom_hist.GetYaxis().SetRangeUser(0., 5.)


class TitleBox(dec.Decorator):

    def make_title(self):
        return "subclass TitleBox and overwrite get_title()!"

    def do_final_cosmetics(self):
        self.decoratee.do_final_cosmetics()

        titlebox = TPaveText(0.18, 0.94, 0.9, 0.97, "brNDC")
        titlebox.AddText(self.make_title())
        titlebox.SetTextSize(0.045)
        titlebox.SetFillStyle(0)
        titlebox.SetBorderSize(0)
        titlebox.SetTextAlign(13)
        titlebox.SetMargin(0.0)
        titlebox.SetFillColor(0)
        titlebox.Draw("SAME")
        self.titlebox = titlebox


#TODO: Statbox from classes/CRUtilities
#TODO: Stuff from tools/CRHistoStackerDecorators


