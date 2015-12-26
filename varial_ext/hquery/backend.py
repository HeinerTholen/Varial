from varial_ext.treeprojector import TreeProjector, BatchTreeProjector
from varial.main import _process_settings_kws
from varial.webcreator import WebCreator


class HQueryBackend(object):
    def __init__(self, kws, q_in, q_out):
        assert 'filenames' in kws, '"filenames" is needed.'
        assert 'treename' in kws, '"treename" is needed.'
        if 'backend' in kws:
            assert kws['backend'] in ('local', 'sge'), 'may be "local" or "sge"'
            backend_type = kws.pop('backend')
        else:
            backend_type = 'local'

        self.q_in = q_in
        self.q_out = q_out

        if backend_type == 'local':
            TP = TreeProjector
        else:
            TP = BatchTreeProjector

        histos = dict(self.make_histo_item(t) for t in kws.pop('histos', []))
        self.params = dict(histos=histos, treename=kws.pop('treename'))
        self.tp = TP(kws.pop('filenames'), self.params,
                     add_aliases_to_analysis=False, name='_Backend')
        self.wc = WebCreator(name='hQuery', no_tool_check=True)
        self.wc.run()
        self.job_submitter = None  # TODO
        _process_settings_kws(kws)

    @staticmethod
    def make_histo_item(tple):
        assert len(tple) == 5, 'need name,title,bins,low,high; got %s' % tple
        name, title, bins, lo, hi = tple
        assert isinstance(name, str)
        assert isinstance(title, str)
        assert isinstance(bins, int)
        assert isinstance(lo, int) or isinstance(lo, float)
        assert isinstance(hi, int) or isinstance(hi, float)
        return name, (title, bins, lo, hi)

    def process_request(self, args, kws):
        pass
        # varial.analysis.reset()

    def start(self):
        self.q_out.put('backend ready')
        while True:
            nxt = None
            try:
                nxt = self.q_in.get()
            except KeyboardInterrupt:
                exit(0)
            if nxt == 'terminate':
                exit(0)
            print nxt
            self.q_out.put(nxt)
