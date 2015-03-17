"""
Limit derivation with theta: http://theta-framework.org
"""

import os
import ROOT

import varial.tools
import theta_auto
theta_auto.config.theta_dir = os.environ["CMSSW_BASE"] + "/theta"


class ThetaLimits(varial.tools.Tool):
    def __init__(
        self,
        input_path='../HistoLoader',
        asymptotic=True,
        dat_key=lambda w: w.is_data or w.is_pseudo_data,
        sig_key=lambda w: w.is_signal,
        bkg_key=lambda w: not any((w.is_signal, w.is_data, w.is_pseudo_data)),
        name=None,
    ):
        super(ThetaLimits, self).__init__(name)
        self.input_path = input_path
        self.asymptotic = asymptotic
        self.dat_key = dat_key
        self.sig_key = sig_key
        self.bkg_key = bkg_key

    def _store_histos_for_theta(self, dat, sigs, bkgs):
        # create wrp
        wrp = varial.wrappers.Wrapper(name="ThetaHistos")
        if dat:
            setattr(wrp, 'histo__DATA', dat[0].histo)
        for bkg in bkgs:
            setattr(wrp, 'histo__bkg_' + bkg.sample, bkg.histo)
        for sig in sigs:
            setattr(wrp, 'histo__sig_' + sig.sample, sig.histo)

        # write manually
        filename = os.path.join(varial.analysis.cwd, wrp.name + ".root")
        f = ROOT.TFile.Open(filename, "RECREATE")
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

        dat = filter(self.dat_key, wrps)
        sig = filter(self.sig_key, wrps)
        bkg = filter(self.bkg_key, wrps)

        # do some basic input check
        if not bkg:
            raise RuntimeError('No background histograms present.')
        if not sig:
            raise RuntimeError('No signal histograms presen.t')
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
        self.model = theta_auto.build_model_from_rootfile(
            os.path.join(self.cwd, 'ThetaHistos.root'),
            include_mc_uncertainties=True
        )
        self.model.fill_histogram_zerobins()
        self.model.set_signal_processes(list(
            k[7:]
            for k in theta_wrp.__dict__
            if k.startswith('histo__sig_')
        ))

        # let the fit run
        options = theta_auto.Options()
        options.set('minimizer', 'strategy', 'robust')
        limit_func = theta_auto.asymptotic_cls_limits \
            if self.asymptotic else theta_auto.bayesian_limits
        res_exp, res_obs = limit_func(
            self.model,
            #what='expected'
        )

        # shout it out loud
        self.result = varial.wrappers.Wrapper(
            name=self.name,
            res_exp=str(res_exp),
            res_obs=str(res_obs),
        )
        self.message(
            'INFO theta result: expected limit:\n' + self.result.res_exp)
        self.message(
            'INFO theta result: expected limit:\n' + self.result.res_obs)
        theta_auto.config.report.write_html(
            os.path.join(self.cwd, 'result'))


