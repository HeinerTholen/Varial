"""
Limit derivation with theta: http://theta-framework.org
"""

import os
import ROOT

import varial.tools
import varial.analysis
import theta_auto
theta_auto.config.theta_dir = os.environ["CMSSW_BASE"] + "/../theta"


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
            _res_exp=res_exp,
            _res_obs=res_obs,
            res_exp_x=res_exp.x,
            res_exp_y=res_exp.y,
            res_exp_xerrors=res_exp.xerrors,
            res_exp_yerrors=res_exp.yerrors,
        )
        theta_auto.config.report.write_html(
            os.path.join(self.cwd, 'result'))