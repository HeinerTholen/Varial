import os
import subprocess
import time

import analysis
import diskio
import settings
import toolinterface


class FwliteProxy(toolinterface.Tool):
    def __init__(self,
                 name=None,
                 py_exe=None):
        super(FwliteProxy, self).__init__(name)
        self.py_exe = py_exe or settings.fwlite_executable
        self._proxy = None

    def wanna_reuse(self, all_reused_before_me):
        if not os.path.exists(os.path.join(
                self.result_dir, 'fwlite_proxy.info')):
            return False
        proxy = diskio.read('fwlite_proxy')
        if not hasattr(proxy, 'results'):
            return False
        for name, smp in analysis.all_samples.iteritems():
            if not (
                name in proxy.samples
                and proxy.samples[name] == smp.input_files
            ):
                return False
        self._proxy = proxy
        return True

    def reuse(self):
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

        self._proxy = analysis.fileservice('fwlite_proxy', False)
        self._proxy.event_files = dict(
            (s.name, s.input_files)
            for s in analysis.all_samples.itervalues()
        )
        diskio.write(self._proxy)
        proc = subprocess.Popen(['python', self.py_exe])
        sig_term_sent = False
        while None == proc.returncode:
            if settings.recieved_sigint and not sig_term_sent:
                proc.terminate()
                sig_term_sent = True
            time.sleep(0.2)
            proc.poll()
        if proc.returncode:
            raise RuntimeError(
                'FwLite subprocess returned %d' % proc.returncode)
        self._finalize()

    def _finalize(self):
        if settings.recieved_sigint:
            return
        for res in self._proxy.results:
            samplename = res.split('!')[0]
            analysis.fs_aliases += list(
                alias for alias in diskio.generate_fs_aliases(
                    os.path.join(self.result_dir, '%s.root' % res),
                    samplename
                )
            )