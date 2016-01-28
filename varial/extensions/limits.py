"""
Limit derivation with theta: http://theta-framework.org
"""

import cPickle
import ROOT
import os

import varial.sparseio
import varial.analysis
import varial.tools
import varial.pklio

import theta_auto
theta_auto.config.theta_dir = os.environ['CMSSW_BASE'] + '/../theta'


tex_table_mod_list = [
    ('_', '\_'),        # escape underscore
    ('\_{', '_{'),      # un-escape subscripts
    ('\_', ' '),        # remove underscores
    ('(gauss)', ' '),
]


def tex_table_mod(table, mods=None):
    mods = mods or tex_table_mod_list
    for mod in mods:
        table = table.replace(*mod)
    return table


######################################################### limit calculation ###
class ThetaLimits(varial.tools.Tool):
    def __init__(
        self,
        model_func,
        input_path='../HistoLoader',
        input_path_sys='../HistoLoaderSys',
        filter_keyfunc=None,
        asymptotic=True,
        cat_key=lambda _: 'histo',  # lambda w: w.category,
        dat_key=lambda w: w.is_data or w.is_pseudo_data,
        sig_key=lambda w: w.is_signal,
        bkg_key=lambda w: w.is_background,
        sys_key=None,
        tex_table_mod=tex_table_mod,
        name=None,
    ):
        super(ThetaLimits, self).__init__(name)
        self.model_func = model_func
        self.input_path = input_path
        self.input_path_sys = input_path_sys
        self.filter_keyfunc = filter_keyfunc
        self.asymptotic = asymptotic
        self.cat_key = cat_key
        self.dat_key = dat_key
        self.sig_key = sig_key
        self.bkg_key = bkg_key
        self.sys_key = sys_key
        self.tex_table_mod = tex_table_mod
        self.model = None
        self.what = 'all'

    def prepare_dat_sig_bkg(self, wrps):
        if self.filter_keyfunc:
            wrps = list(w for w in wrps if self.filter_keyfunc(w))

        dats = list(w for w in wrps if self.dat_key(w))
        sigs = list(w for w in wrps if self.sig_key(w))
        bkgs = list(w for w in wrps if self.bkg_key(w))

        # do some basic input check
        assert bkgs, 'no background histograms present.'
        assert sigs, 'no signal histograms present.'
        if not dats:
            self.message('WARNING No data histogram, only expected limits.')
            self.what = 'expected'

        return dats, sigs, bkgs

    def add_nominal_hists(self, wrp):
        wrps = self.lookup_result(self.input_path)
        assert wrps, 'no input for path: %s' % self.input_path
        dats, sigs, bkgs = self.prepare_dat_sig_bkg(wrps)

        for w in dats:
            setattr(wrp, self.cat_key(w) + '__DATA', w.histo)
        for w in bkgs:
            setattr(wrp, self.cat_key(w) + '__' + w.sample, w.histo)
        for w in sigs:
            setattr(wrp, self.cat_key(w) + '__' + w.sample, w.histo)

    def add_sys_hists(self, wrp):
        wrps = self.lookup_result(self.input_path_sys)
        if not wrps:
            return
        assert self.sys_key, 'sys_key is required. e.g. lambda w: w.sys_type'
        _, sigs, bkgs = self.prepare_dat_sig_bkg(wrps)

        def mk_name(w, sample=''):
            category = self.cat_key(w)
            sys = self.sys_key(w)
            return category + '__' + (sample or w.sample) + '__' + sys

        for w in bkgs:
            setattr(wrp, mk_name(w), w.histo)
        for w in sigs:
            setattr(wrp, mk_name(w), w.histo)

    @staticmethod
    def store_histos_for_theta(wrp):
        # write manually
        f = ROOT.TFile.Open(wrp.file_path, "RECREATE")
        f.cd()
        for key, value in wrp.__dict__.iteritems():
            if isinstance(value, ROOT.TH1):
                value.SetName(key)
                value.Write()
        f.Close()
        return wrp

    def run(self):
        # create wrp
        wrp = varial.wrappers.Wrapper(
            name='ThetaHistos',
            file_path=os.path.join(self.cwd, 'ThetaHistos.root'),
        )

        # add histograms and store for theta
        self.add_nominal_hists(wrp)
        self.add_sys_hists(wrp)
        self.store_histos_for_theta(wrp)
        
        # setup theta
        theta_auto.config.workdir = self.cwd
        theta_auto.config.report = theta_auto.html_report(
            os.path.join(self.cwd, 'report.html')
        )
        plt_dir = os.path.join(self.cwd, 'plots')
        if not os.path.exists(plt_dir):
            os.mkdir(plt_dir)
        self.model = self.model_func(wrp.file_path)

        # let the fit run
        options = theta_auto.Options()
        options.set('minimizer', 'strategy', 'robust')
        if self.asymptotic:
            limit_func = theta_auto.asymptotic_cls_limits
        else:
            limit_func = lambda m: theta_auto.bayesian_limits(m, what=self.what)

        self.message('INFO calling theta func: %s' % (
            'asymptotic_cls_limits' if self.asymptotic else 'bayesian_limits'))
        res_exp, res_obs = limit_func(self.model)

        self.message('INFO fetching post-fit parameters')
        postfit = theta_auto.mle(self.model, input='data', n=1, options=options)

        # shout it out loud
        summary = theta_auto.model_summary(self.model)
        theta_auto.config.report.write_html(os.path.join(self.cwd, 'result'))

        with open(self.cwd + 'rate_table.tex', 'w') as f:
            f.write(
                self.tex_table_mod(
                    summary['rate_table'].tex()))

        for proc, table in summary['sysrate_tables'].iteritems():
            with open(self.cwd + 'sysrate_tables_%s.tex' % proc, 'w') as f:
                f.write(
                    self.tex_table_mod(
                        table.tex()))

        self.result = varial.wrappers.Wrapper(
            name=self.name,
            res_exp_x=res_exp.x,
            res_exp_y=res_exp.y,
            res_exp_xerrors=res_exp.xerrors,
            res_exp_yerrors=res_exp.yerrors,
            res_obs_x=res_obs.x,
            res_obs_y=res_obs.y,
            res_obs_xerrors=res_obs.xerrors,
            res_obs_yerrors=res_obs.yerrors,

            # in order to access details, one must unpickle.
            res_exp=cPickle.dumps(res_exp),
            res_obs=cPickle.dumps(res_obs),
            summary=cPickle.dumps(summary),
            postfit_vals=postfit,
        )


################################################## plot nuisance parameters ###
class ThetaPostFitPlot(varial.tools.Tool):
    io = varial.pklio

    def __init__(
        self,
        input_path='../ThetaLimits',
        name=None,
    ):
        super(ThetaPostFitPlot, self).__init__(name)
        self.input_path = input_path

    @staticmethod
    def prepare_post_fit_items(post_fit_dict):
        return list(
            (name, val_err)
            for name, (val_err,) in sorted(post_fit_dict.iteritems())
            if name not in ('__nll', 'beta_signal')
        )

    @staticmethod
    def prepare_pull_graph(n_items, post_fit_items):
        g = ROOT.TGraphAsymmErrors(n_items)
        for i, (_, (val, err)) in enumerate(post_fit_items):
            x, y = val, i + 1.5
            g.SetPoint(i, x, y)
            g.SetPointEXlow(i, err)
            g.SetPointEXhigh(i, err)

        g.SetLineStyle(1)
        g.SetLineWidth(1)
        g.SetLineColor(1)
        g.SetMarkerStyle(21)
        g.SetMarkerSize(1.25)
        return g

    @staticmethod
    def prepare_band_graphs(n_items):
        g68 = ROOT.TGraph(2*n_items+7)
        g95 = ROOT.TGraph(2*n_items+7)
        for a in xrange(0, n_items+3):
            g68.SetPoint(a, -1, a)
            g95.SetPoint(a, -2, a)
            g68.SetPoint(a+1+n_items+2, 1, n_items+2-a)
            g95.SetPoint(a+1+n_items+2, 2, n_items+2-a)
        g68.SetFillColor(ROOT.kGreen)
        g95.SetFillColor(ROOT.kYellow)
        return g68, g95

    @staticmethod
    def prepare_canvas(name):
        c_name = 'cnv_post_fit_' + name
        c = ROOT.TCanvas(c_name, c_name, 600, 700)
        c.SetTopMargin(0.06)
        c.SetRightMargin(0.02)
        c.SetBottomMargin(0.12)
        c.SetLeftMargin(0.35*700/650)
        c.SetTickx()
        c.SetTicky()
        return c

    @staticmethod
    def put_axis_foo(n_items, prim_graph, post_fit_items):
        prim_hist = prim_graph.GetHistogram() 
        ax_1 = prim_hist.GetYaxis()
        ax_2 = prim_hist.GetXaxis()

        prim_graph.SetTitle('')
        ax_2.SetTitle('post-fit nuisance parameters values')
        #ax_2.SetTitle('deviation in units of #sigma')
        ax_1.SetTitleSize(0.050)
        ax_2.SetTitleSize(0.050)
        ax_1.SetTitleOffset(1.4)
        ax_2.SetTitleOffset(1.0)
        ax_1.SetLabelSize(0.05)
        #ax_2.SetLabelSize(0.05)
        ax_1.SetRangeUser(0, n_items+2)
        ax_2.SetRangeUser(-2.4, 2.4)

        ax_1.Set(n_items+2, 0, n_items+2)
        ax_1.SetNdivisions(-414)
        for i, (uncert_name, _) in enumerate(post_fit_items):
            ax_1.SetBinLabel(i+2, uncert_name)

    def mk_canvas(self, sig_name, post_fit_dict):
        n = len(post_fit_dict)
        items = self.prepare_post_fit_items(post_fit_dict)
        
        g = self.prepare_pull_graph(n, items)
        g68, g95 = self.prepare_band_graphs(n)
        cnv = self.prepare_canvas(sig_name)

        cnv.cd()
        g95.Draw('AF')
        g68.Draw('F')
        g.Draw('P')
        
        self.put_axis_foo(n, g95, items)
        g95.GetHistogram().Draw('axis,same')
        cnv.Modified()
        cnv.Update()

        return varial.wrp.CanvasWrapper(
            cnv, post_fit_items=items, pulls=g, g95=g95, g68=g68)

    def run(self):
        theta_res = self.lookup_result(self.input_path)
        cnvs = (self.mk_canvas(sig, pfd) 
                for sig, pfd in theta_res.postfit_vals.iteritems())

        cnvs = varial.sparseio.bulk_write(cnvs, lambda c: c.name)
        self.result = list(cnvs)
