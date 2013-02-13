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
                    if histo.GetBinContent(i) > 1e-43
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
      renderers are created automaticly.

    * ``**kws`` can be empty. Accepted keywords are ``name=`` and ``title=`` and
      any keyword that is accepted by ``histotools.wrappers.CanvasWrapper``.

    When designing decorators, these instance data members can be of interest:

    ================= =========================================================
    ``x_bounds``      Bounds of canvas area in x
    ``y_bounds``      Bounds of canvas area in y
    ``y_min_gr_zero`` smallest y greater zero (need in log plotting)
    ``canvas``        Reference to the TCanvas instance
    ``main_pad``      Reference to TPad instance
    ``first_drawed``  TObject which is first drawed (for valid TAxis reference)
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
    first_drawed   = None
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
        rnds = self.renderers
        for i, rnd in enumerate(rnds):
            if not i:
                self.first_drawed = rnd.primary_object()
                self.first_drawed.SetTitle("")
                rnd.draw("")
            else:
                rnd.draw("same")

    def do_final_cosmetics(self):
        """Pimp the canvas!"""
        y_min, y_max = self.y_bounds
        self.first_drawed.SetMinimum(y_min * 0.9)
        self.first_drawed.SetMaximum(y_max * 1.1)

    def run_procedure(self):
        """
        This method calls all other methods, which fill and build the canvas.
        """
        self.configure()
        self.find_x_y_bounds()
        self.make_empty_canvas()
        self.draw_full_plot()
        self.do_final_cosmetics()

    def _del_builder_refs(self):
        for k,obj in self.__dict__.items():
            if isinstance(obj, TObject):
                setattr(self, k, None)

    def build_canvas(self):
        """
        With this method, the building procedure is started.

        :return: ``CanvasWrapper`` instance.
        """
        canvas = self.canvas
        if not canvas:
            self.run_procedure()
        wrp = wrappers.CanvasWrapper(self.canvas, **self.kws)
        self._del_builder_refs()
        return wrp

############################################# customization with decorators ###
from cmstoolsac3b.decorator import Decorator
from ROOT import TLegend

class Legend(Decorator):
    """
    Adds a legend to the main_pad.

    Takes entries from ``self.main_pad.BuildLegend()`` .
    The box height is adjusted by the number of legend entries.
    No border or shadow are printed. Keyword
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

    def do_final_cosmetics(self):
        """
        Only ``do_final_cosmetics`` is overwritten here.

        If self.legend == None, this method will create a default legend and
        store it to self.legend
        """
        if self.legend: return

        tmp_leg = self.main_pad.BuildLegend(0.1, 0.6, 0.5, 0.8) # get legend entry objects
        tobjects = [(entry.GetObject(), entry.GetLabel())
                    for entry in tmp_leg.GetListOfPrimitives()]
        tmp_leg.Clear()
        self.main_pad.GetListOfPrimitives().Remove(tmp_leg)
        tmp_leg.Delete()

        par = self.dec_par
        x1, x2, y2, y_shift = par["x1"], par["x2"], par["y2"], par["y_shift"]
        y1 = y2 - (len(tobjects) * y_shift)
        legend = TLegend(x1, y1, x2, y2)
        legend.SetBorderSize(0)
        if par["reverse"]:
            tobjects.reverse()
        for obj in tobjects:
            if obj[1] == "Data" or obj[1] == "data":
                legend.AddEntry(
                    obj[0],
                    obj[1],
                    par["opt_data"]
                )
            else:
                legend.AddEntry(
                    obj[0],
                    obj[1],
                    par["opt"]
                )
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



#TODO: Statbox from classes/CRUtilities
#TODO: Stuff from tools/CRHistoStackerDecorators
