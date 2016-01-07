from varial_ext.treeprojector import TreeProjector, BatchTreeProjector
from varial.plotter import mk_rootfile_plotter
from varial.main import process_settings_kws
from varial.webcreator import WebCreator
from varial.tools import Runner
import varial

import string
import shutil
import json
import glob
import time
import os


SECTION_CHARS = '-_.' + string.ascii_letters + string.digits


class HistoTypeSpecifier(object):
    def __init__(self, signals, data):
        assert isinstance(signals, list)
        assert isinstance(data, list)
        self.signals = signals
        self.data = data

    def __call__(self, wrps):
        return varial.gen.gen_add_wrp_info(
            wrps,
            is_signal=lambda w: w.sample in self.signals,
            is_data=lambda w: w.sample in self.data,
        )


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

        if not os.path.exists('sections'):
            os.mkdir('sections')
            os.system('touch sections/webcreate_request')

        histos = kws.pop('histos', {})
        for name, tple in histos.iteritems():
            self.check_histo_item(name, tple)
        self.params = dict(histos=histos,
                           treename=kws.pop('treename'),
                           nm1=False)
        self.sel_info = {}
        self.sec_sel_weight = {}  # sec -> (sec, sel, weight)
        weight, msg = kws.pop('weight', ''), 'weight can be str or dict'
        assert isinstance(weight, str) or isinstance(weight, dict), msg
        self.weight = weight

        if backend_type == 'local':
            TP = TreeProjector
        else:
            TP = BatchTreeProjector
        self.tp = TP(kws.pop('filenames'),
                     self.params,
                     add_aliases_to_analysis=False,
                     name='treeprojector')
        self.tp.reset = lambda: None
        self.stack = kws.pop('stack', False)
        self.plotter_hook = HistoTypeSpecifier(kws.pop('signal_samples', []),
                                               kws.pop('data_samples', []))
        self.wc = WebCreator(name='hQuery', no_tool_check=True)
        self.wc.working_dir = 'sections'
        self.wc.update()
        varial.settings.no_toggles = True

        self.dump_python_conf = kws.pop('dump_python_conf', False)
        process_settings_kws(kws)

    def read_settings(self):
        if not os.path.exists('params.json'):
            return False
        with open('params.json') as f:
            self.params, self.sec_sel_weight, self.sel_info = json.load(f)
        return True

    def write_settings(self):
        with open('params.json', 'w') as f:
            json.dump((self.params, self.sec_sel_weight, self.sel_info), f)
        if self.dump_python_conf:
            self.write_histos()
            self.write_sec_sel_weight()

    def write_histos(self):
        with open('params_histos.py', 'w') as f:
            f.write(repr(self.params['histos']))

    def write_sec_sel_weight(self):
        with open('params_sec_sel_weight.py', 'w') as f:
            f.write(repr(self.sec_sel_weight))

    def make_branch_name_json(self):
        import ROOT
        plain_types = {'int': int, 'float': float, 'long': long, 'bool': bool}
        plain_types_list = plain_types.values()
        plain_c_types = plain_types.keys() + ['double', 'short']

        def handle_item(name, item, depth):
            if item is None or depth > 1:
                return []

            item_typ = type(item)
            if item_typ in plain_types_list:
                return [name]
            elif 'vector<' in str(item_typ):
                data_typ = str(item_typ).split('vector<')[1].split('>')[0]
                if data_typ in plain_types:
                    return [name, '@%s.size()' % name]
                else:
                    typ_inst = getattr(ROOT, data_typ)()
                    object_items = handle_item('', typ_inst, depth)
                    object_items = list(
                        name + conj + res
                        for res in object_items
                        for conj in ('.', '[0].')
                    )
                    return ['@%s.size()' % name] + object_items

            elif callable(item):
                func_doc = getattr(item, 'func_doc', '')
                if func_doc.startswith('void '):
                    return []
                elif any(func_doc.startswith(t + ' ') for t in plain_c_types):
                    return [name+'()']
                else:
                    return []

            else:
                name = name + '.' if name else ''
                return list(
                    name + res
                    for funcname in dir(item)
                    if not funcname.startswith('_')
                    for res in handle_item(
                        funcname, getattr(item, funcname), depth+1)
                )

        treename = self.params['treename']
        if self.plotter_hook.data:
            filename = self.tp.filenames[self.plotter_hook.data[0]][0]
        else:
            filename = next(self.tp.filenames.itervalues())[0]
        f = ROOT.TFile(filename)
        t = f.Get(treename)
        t = next(iter(t))
        names = list(b.GetName() for b in t.GetListOfBranches())
        names = list(
            res
            for bname in names
            for res in handle_item(bname, getattr(t, bname), 0)
        )
        f.Close()
        with open('sections/branch_names.json', 'w') as f:
            json.dump(names, f)

    def run_webcreator(self):
        self.wc.run()
        self.wc.reset()
        varial.analysis.reset()

    def run_treeprojection(self, section=None):
        if section:
            ssw = [self.sec_sel_weight[section]]
        else:
            ssw = list(self.sec_sel_weight.itervalues())

        if not (ssw and self.params['histos']):
            return

        self.q_out.put('Filling histograms in: ' + ', '.join(s[0] for s in ssw))
        self.tp.sec_sel_weight = ssw
        self.tp.params = self.params
        self.tp.update()
        Runner(self.tp)
        self.tp.reset()
        Runner(mk_rootfile_plotter(
            name='sections',
            pattern='treeprojector/*.root',
            combine_files=True,
            hook_loaded_histos=self.plotter_hook,
            stack=self.stack,
        ))

    @staticmethod
    def check_histo_item(name, tple):
        assert len(tple) == 4, 'need title,bins,low,high; got %s' % tple
        title, bins, lo, hi = tple
        assert isinstance(name, str), repr(name)
        assert isinstance(title, str), repr(title)
        assert isinstance(bins, int), repr(bins)
        assert isinstance(lo, int) or isinstance(lo, float), repr(lo)
        assert isinstance(hi, int) or isinstance(hi, float), repr(hi)

    def create_new_section(self, name, from_section=None):
        # checks
        if any(c not in SECTION_CHARS for c in name):
            raise RuntimeError(
                'Section names may only contain "%s". Got "%s".'
                % (SECTION_CHARS, name)
            )
        if os.path.exists('sections/' + name):
            raise RuntimeError('Section exists: ' + name)

        if from_section:  # copy
            shutil.copytree('sections/' + from_section, 'sections/' + name)
            sel = self.sec_sel_weight[from_section][1]
            self.sec_sel_weight[name] = (name, sel[:], self.weight)
            self.sel_info[name] = dict(self.sel_info[from_section])

        else:  # create from scratch
            os.mkdir('sections/' + name)
            with open('sections/' + name + '/webcreate_request', 'w') as f:
                f.write('(enable webcreation also for empty folders)\n')
            self.sec_sel_weight[name] = (name, [], self.weight)
            self.sel_info[name] = {}

        self.q_out.put('Section created: ' + name)
        self.run_webcreator()
        self.q_out.put('redirect:/{}/index.html'.format(name))

        if not from_section:  # run treeprojection if not copied
            self.run_treeprojection(name)

    def delete_section(self, name):
        if not os.path.exists('sections/' + name):
            raise RuntimeError('Section does not exists: ' + name)

        shutil.rmtree('sections/' + name)
        del self.sec_sel_weight[name]
        del self.sel_info[name]

        self.q_out.put('Section deleted: ' + name)

    def create_histogram(self, kws):
        name = str(kws['hidden_histo_name'] or kws['histo_name'])
        bins, low, high = kws['bins'], kws['low'], kws['high']

        # checks
        assert_msg = 'Either "bins" or "low" *and* "high" needed. Or all.'
        assert bins or (low and high), assert_msg
        assert bool(low) == bool(high), assert_msg
        bins = int(kws['bins'] or 40)
        if not low:
            bins, low, high = bins + 1, -.5, bins + .5
        params = (str(kws['title']), bins, float(low), float(high))
        self.check_histo_item(name, params)

        # run sections with new histo
        self.params['histos'][name] = params
        self.q_out.put('Histogram defined: ' + name)
        try:  # if something goes wrong, the histo must be removed
            self.run_treeprojection()
        except RuntimeError:
            del self.params['histos'][name]
            raise
        self.q_out.put('redirect:index.html#{}'.format(name))

    def delete_histogram(self, name):
        del self.params['histos'][name]
        names = list(name + tok +'.png' for tok in ('_lin', '_log', ''))
        for section in self.sec_sel_weight:
            p = os.path.join('sections', section)
            for f in os.listdir(p):
                if f in names:
                    os.remove(os.path.join(p, f))

        self.q_out.put('Histogram deleted: ' + name)

    def apply_selection(self, section, kws):
        self.params['nm1'] = 'nm1' in kws
        var, low, high = kws['selection_var'], kws['cut_low'], kws['cut_high']

        # compile selection string
        if low and high:
            if float(low) <= float(high):
                sel = '({lo} <= {var} && {var} < {hi})'
            else:
                sel = '({lo} <= {var} || {var} < {hi})'
        elif low:
            sel = '{lo} <= {var}'
        elif high:
            sel = '{var} < {hi}'
        else:
            sel = ''

        # apply selection
        sel_list = self.sec_sel_weight[section][1]
        sel_list = list(s for s in sel_list if var not in s)  # clean old stuff
        if sel:
            sel = sel.format(lo=low, hi=high, var=var)
            sel_list.append(sel)
            self.q_out.put('Selection defined: ' + sel)
        else:
            self.q_out.put('Selection removed for: ' + var)
        self.sec_sel_weight[section] = (section, sel_list, self.weight)

        # run section with new selection
        try:  # if something goes wrong, the selection must be removed
            self.run_treeprojection(section)
        except RuntimeError:
            sel_list = list(s for s in sel_list if var not in s)
            self.sec_sel_weight[section] = (section, sel_list, self.weight)
            raise
        self.sel_info[section][var] = (low, high)

    def process_request(self, item):
        varial.monitor.message(
            'HQueryBackend.process_request',
            'INFO got request %s' % repr(item),
        )

        if isinstance(item, tuple) and item and item[0] == 'post':
            _, args, kws = item

            # new section
            if 'create section' in kws:
                self.create_new_section(
                    kws['create section'],
                    args[0] if len(args) == 2 else None
                )

            # delete section
            elif 'delete section' in kws:
                self.delete_section(kws['delete section'])

            # create histo
            elif 'hidden_histo_name' in kws:
                self.create_histogram(kws)

            # delete histo
            elif 'delete histogram' in kws:
                self.delete_histogram(kws['delete histogram'])

            # apply selection
            elif 'selection_var' in kws:
                self.apply_selection(args[0], kws)

            else:
                raise RuntimeError('Request not understood %s' % repr(item))
        else:
            raise RuntimeError('Request not understood %s' % repr(item))

        self.run_webcreator()
        self.write_settings()

    def start(self):
        self.q_out.put('backend alive')
        time.sleep(0.01)  # leave thread
        if not self.read_settings():
            self.run_treeprojection()
            self.run_webcreator()
            self.make_branch_name_json()
            self.write_settings()
        self.q_out.put('task done')
        while True:
            item = None

            # get request item
            try:
                item = self.q_in.get()
            except KeyboardInterrupt:
                exit(0)
            if item == 'terminate':
                exit(0)

            # process request
            try:
                self.process_request(item)
            except (RuntimeError, AssertionError), e:
                msg = 'ERROR: %s' % e.message
                varial.monitor.message('HQueryBackend.process_request', msg)
                self.q_out.put(msg)
            self.q_out.put('task done')
