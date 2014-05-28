import subprocess
import time
from os.path import exists, join

import analysis
import diskio
import settings
import toolinterface
import wrappers


class FwliteProxy(toolinterface.Tool):
    def __init__(self,
                 name=None,
                 py_exe=None,
                 use_mp=None):
        super(FwliteProxy, self).__init__(name)
        self.py_exe = py_exe or settings.fwlite_executable
        if None == use_mp:
            self.use_mp = settings.fwlite_use_mp
        else:
            self.use_mp = use_mp
        self._proxy = None

    def wanna_reuse(self, all_reused_before_me):
        proxy = diskio.get('fwlite_proxy')

        # has been working at all?
        if not proxy:
            return False

        # check if result was deleted on disk
        if not all(
            exists(join(self.result_dir, '%s.info' % res))
            for res in proxy.results
        ):
            return False

        # check if all files are done
        files_done = proxy.files_done
        if not all(
            f in files_done
            for smp in analysis.all_samples.itervalues()
            for f in smp.input_files
        ):
            return False
        self._proxy = proxy
        return True

    def reuse(self):
        super(FwliteProxy, self).reuse()
        self._finalize()

    def run(self):
        if settings.suppress_eventloop_exec:
            self.message(
                self, "INFO settings.suppress_eventloop_exec == True, pass...")
            return
        if not (settings.not_ask_execute or raw_input(
                "Really run fwlite jobs on these samples:\n   "
                + ",\n   ".join(map(str, analysis.all_samples.keys()))
                + ('\nusing %i cores' % settings.max_num_processes)
                + "\n?? (type 'yes') "
                ) == "yes"):
            return

        # prepare proxy file
        self._make_proxy()

        # start subprocess
        proc = subprocess.Popen(
            ['python', self.py_exe],
            cwd=self.result_dir
        )

        # block while finished
        sig_term_sent = False
        while None == proc.returncode:
            if settings.recieved_sigint and not sig_term_sent:
                proc.terminate()
                sig_term_sent = True
            time.sleep(0.2)
            proc.poll()

        # final
        if proc.returncode:
            self.message('FATAL subprocess has non zero returncode')
            raise RuntimeError(
                'FwLite subprocess returned %d' % proc.returncode)
        self._finalize()

    def _make_proxy(self):
        self._proxy = diskio.get(
            'fwlite_proxy',
            wrappers.Wrapper(name='fwlite_proxy', files_done={}, results={})
        )
        self._proxy.use_mp = self.use_mp
        self._proxy.event_files = dict(
            (s.name, s.input_files)
            for s in analysis.all_samples.itervalues()
        )

        # if a result was deleted, remove all associated files from files_done
        files_done = self._proxy.files_done
        results = self._proxy.results
        resetted_samples = {}
        for res in results.keys():
            if not exists(join(self.result_dir, '%s.info' % res)):
                del results[res]
                smpl = res.split('!')[0]
                if smpl in resetted_samples:
                    continue
                resetted_samples[smpl] = True
                files = analysis.all_samples[smpl].input_files
                for f in files:
                    if f in files_done:
                        del files_done[f]

        diskio.write(self._proxy)

    def _finalize(self):
        if settings.recieved_sigint:
            return
        for res in self._proxy.results:
            samplename = res.split('!')[0]
            analysis.fs_aliases += list(
                alias for alias in diskio.generate_fs_aliases(
                    join(self.result_dir, '%s.root' % res),
                    analysis.all_samples[samplename]
                )
            )