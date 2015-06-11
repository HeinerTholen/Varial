"""
Limit derivation with theta: http://theta-framework.org
"""

import os
import ROOT

import varial.tools
import varial.analysis
import theta_auto
theta_auto.config.theta_dir = os.environ["CMSSW_BASE"] + "/theta"


class ThetaLimits(varial.tools.Tool):
    def __init__(
        self,
        model_func,
        input_path='../HistoLoader',
        filter_keyfunc=None,
        asymptotic=True,
        cat_key=lambda _: 'histo',  # lambda w: w.category,
        dat_key=lambda w: w.is_data or w.is_pseudo_data,
        sig_key=lambda w: w.is_signal,
        bkg_key=lambda w: not any((w.is_signal, w.is_data, w.is_pseudo_data)),
        name=None,
    ):
        super(ThetaLimits, self).__init__(name)
        self.model_func = model_func
        self.input_path = input_path
        self.filter_keyfunc = filter_keyfunc
        self.asymptotic = asymptotic
        self.cat_key = cat_key
        self.dat_key = dat_key
        self.sig_key = sig_key
        self.bkg_key = bkg_key

    def _store_histos_for_theta(self, dats, sigs, bkgs, name="ThetaHistos"):
        # create wrp
        wrp = varial.wrappers.Wrapper(
            name=name,
            file_path=os.path.join(self.cwd, name + ".root"),
        )
        for w in dats:
            category = self.cat_key(w)
            setattr(wrp, category + '__DATA', w.histo)
        for w in bkgs:
            category = self.cat_key(w)
            setattr(wrp, category + '__' + w.sample, w.histo)
        for w in sigs:
            category = self.cat_key(w)
            setattr(wrp, category + '__' + w.sample, w.histo)

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
        wrps = self.lookup_result(self.input_path)
        if not wrps:
            raise RuntimeError('No histograms present.')

        if self.filter_keyfunc:
            wrps = filter(self.filter_keyfunc, wrps)

        dat = filter(self.dat_key, wrps)
        sig = filter(self.sig_key, wrps)
        bkg = filter(self.bkg_key, wrps)

        # do some basic input check
        if not bkg:
            raise RuntimeError('No background histograms present.')
        if not sig:
            raise RuntimeError('No signal histograms present.')
        if len(dat) > 1:
            raise RuntimeError('Too many data histograms present (>1).')
        if not dat:
            self.message('INFO No data histogram, only expected limits.')

        # setup theta
        theta_wrp = self._store_histos_for_theta(dat, sig, bkg)
        theta_auto.config.workdir = self.cwd
        theta_auto.config.report = theta_auto.html_report(os.path.join(
            self.cwd, 'report.html'
        ))
        plt_dir = os.path.join(self.cwd, 'plots')
        if not os.path.exists(plt_dir):
            os.mkdir(plt_dir)
        self.model = self.model_func(theta_wrp.file_path)
        # self.model = theta_auto.build_model_from_rootfile(
        #     os.path.join(self.cwd, 'ThetaHistos.root'),
        #     include_mc_uncertainties=True
        # )
        # self.model.fill_histogram_zerobins()
        # self.model.set_signal_processes(list(
        #     k.split('__')[-1]
        #     for k in theta_wrp.__dict__
        #     if 'TpTp' in k
        # ))
        # # self.model.add_lognormal_uncertainty('ttbar_rate', math.log(1.15), 'TTJets')
        # # self.model.add_lognormal_uncertainty('qcd_rate', math.log(1.30), 'QCD')
        # # self.model.add_lognormal_uncertainty('wjets_rate', math.log(1.25), 'WJets')
        # # self.model.add_lognormal_uncertainty('zjets_rate', math.log(1.50), 'ZJets')
        # # self.model.add_lognormal_uncertainty('signal_rate', math.log(1.15), 'TpTp_M1000')

        # let the fit run
        options = theta_auto.Options()
        options.set('minimizer', 'strategy', 'robust')
        theta_auto.model_summary(self.model)
        if self.asymptotic:
            limit_func = lambda w: theta_auto.asymptotic_cls_limits(w)
        else: limit_func = lambda w: theta_auto.bayesian_limits(w, what='expected')
        res_exp, res_obs = limit_func(self.model)

        # shout it out loud
        self.result = varial.wrappers.Wrapper(
            name=self.name,
            res_exp=res_exp,  # TODO only TObjects or native python objects (list, dict, int, str ...) allowed
            res_obs=res_obs,  # TODO only TObjects or native python objects (list, dict, int, str ...) allowed
        )
        self.message(
            'INFO theta result: expected limit:\n' + str(self.result.res_exp))
        self.message(
            'INFO theta result: expected limit:\n' + str(self.result.res_obs))
        theta_auto.config.report.write_html(
            os.path.join(self.cwd, 'result'))


class TpTpThetaLimits(ThetaLimits):
    def __init__(self,
        brs = None,
        *args,**kws
    ):
        super(TpTpThetaLimits, self).__init__(*args, **kws)
        self.brs = brs

    def run(self):
        super(TpTpThetaLimits, self).run()
        self.result = varial.wrappers.Wrapper(
            name=self.result.name,
            res_exp=self.result.res_exp,
            res_obs=self.result.res_obs,
            brs=self.brs
        )


class TriangleLimitPlots(varial.tools.Tool):
    def __init__(self,
        name=None
    ):
        super(TriangleLimitPlots, self).__init__(name)


    def run(self):
        # parent = varial.analysis.lookup_tool('../.')
        # varial.analysis.print_tool_tree()
        parents = os.listdir(self.cwd+'/..')
        # print parents
        theta_tools = list(k for k in parents if k.startswith("ThetaLimit"))
        # print theta_tools
        wrps = list(self.lookup_result('../' + k) for k in theta_tools)
        filename = os.path.join(varial.analysis.cwd, self.name + ".root")
        f = ROOT.TFile.Open(filename, "RECREATE")
        f.cd()
        tri_hist = ROOT.TH2F("triangular_limits", ";br to th;br to tz", 10, 0., 1., 10, 0., 1.)
        for w in wrps:
            br_th = float(w.brs['th'])
            br_tz = float(w.brs['tz'])
            # limit_f = float(w.res_exp.y[0])
            tri_hist.Fill(br_th, br_tz, w.res_exp.y[0])
        tri_hist.Write()
        f.Close()



