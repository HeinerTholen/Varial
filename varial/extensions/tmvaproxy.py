"""
Varial tmva tool.
"""

import ROOT
assert ROOT.TMVA

from varial import toolinterface


class TmvaProxy(toolinterface.Tool):
    def __init__(
            self,
            name=None,
            sig_filenames=(),
            bkg_filenames=(),
            removed_vars=('weight',),
            spectators=(),
            variables=(),
    ):
        super(TmvaProxy, self).__init__(name)
        self.sig_filenames  = sig_filenames
        self.bkg_filenames  = bkg_filenames
        self.removed_vars   = removed_vars
        self.spectators     = spectators
        self.variables      = variables

        self.sig_trees      = []
        self.bkg_trees      = []

        self.out_file       = None
        self.factory        = None

    def configure(self):
        for fname in self.sig_filenames:
            f = ROOT.TFile(fname)
            treename = fname.split('.')[1]  # todo: make better..
            self.sig_trees.append(f.Get(treename))
        for fname in self.bkg_filenames:
            f = ROOT.TFile(fname)
            treename = fname.split('.')[1]  # todo: make better..
            self.bkg_trees.append(f.Get(treename))

        variables = list(b.GetName()
                         for b in self.bkg_trees[0].GetListOfBranches())
        if self.variables:
            for v in self.variables[:]:
                if v not in variables:
                    self.message('WARNING Variable "%s" not found!' % v)
                    self.variables.remove(v)
        else:
            self.variables = variables

        for v in self.removed_vars:
            if v in self.variables:
                self.variables.remove(v)
            else:
                self.message('WARNING Removed var "%s" not found!' % v)
        for v in self.spectators[:]:
            if v in self.variables:
                self.variables.remove(v)
            else:
                self.spectators.remove(v)
                self.message('WARNING Spectator "%s" not found!' % v)

        self.message('INFO Using variables: ' + str(self.variables))
        self.message('INFO Using spectators: ' + str(self.spectators))

    def setup_tmva(self):
        self.out_file = ROOT.TFile(self.cwd+'TMVA.root', 'RECREATE')
        self.factory = ROOT.TMVA.Factory(
            'TMVAClassification',
            self.out_file,
            '!V:!Silent:Color:DrawProgressBar:Transformations=I'
            ';D;P;G,D:AnalysisType=Classification'
        )
        typs = {int: 'I', float: 'F'}
        for var in self.variables:
            typ = typs[type(getattr(self.bkg_trees[0], var))]
            self.factory.AddVariable(var, var, 'units', typ)
        for var in self.spectators:
            self.factory.AddSpectator(var, var, 'units')
        for t in self.sig_trees:
            self.factory.AddSignalTree(t, 1.0)
            #factory.SetSignalWeightExpression('weight')
        for t in self.bkg_trees:
            self.factory.AddSignaAddBackgroundTreelTree(t, 1.0)
            #factory.SetBackgroundWeightExpression('weight')

    def run(self):
        self.configure()
        self.setup_tmva()


        self.factory.PrepareTrainingAndTestTree(ROOT.TCut(''), 'SplitMode=random:!V')
        self.factory.BookMethod(
            ROOT.TMVA.Types.kCuts,
            'Cuts',
            '!H:!V:FitMethod=MC:EffSel:SampleSize=200000:VarProp=FSmart'
        )

        self.factory.BookMethod(
            ROOT.TMVA.Types.kCuts,
            'CutsD',
            '!H:!V:FitMethod=MC:EffSel:SampleSize=200000:VarProp=FSmart'
        )

        self.factory.BookMethod(
            ROOT.TMVA.Types.kBDT,
            "BDT",
            "!H:!V:NTrees=850:MinNodeSize=2.5%:MaxDepth=3:BoostType=AdaBoost:AdaBoostBeta=0.5:"
            "UseBaggedBoost:BaggedSampleFraction=0.5:SeparationType=GiniIndex:nCuts=20"
        )
        self.factory.TrainAllMethods()
        self.factory.TestAllMethods()
        self.factory.EvaluateAllMethods()
        self.out_file.Close()


        #variables.remove('trigger_accept')
        #variables.remove('vlq_mass')
        #variables = ['n_leptons', 'n_btags', 'n_higgs_tags']
        #variables = ['leading_jet_pt', 'subleading_jet_pt', 'vlq_pt', 'vlq_eta']
