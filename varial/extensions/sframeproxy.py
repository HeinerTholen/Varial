"""
Host sframe processes in a toolchain.
"""

import xml.etree.cElementTree as ElementTree
import subprocess
import time
import os
join = os.path.join
basename = os.path.basename

from varial import analysis
from varial import diskio
from varial import pklio
from varial import settings
from varial import toolinterface
from varial import wrappers


class SFrame(toolinterface.Tool):
    """
    This class hosts a sframe process.

    sframe output is streamed into a logfile.
    """
    io = pklio

    def __init__(self,
                 cfg_filename,
                 xml_tree_callback=None,
                 add_aliases_to_analysis=True,
                 halt_on_exception=True,
                 samplename_func=lambda w: basename(w.file_path).split('.')[3],
                 name=None):
        super(SFrame, self).__init__(name)
        self.cfg_filename           = cfg_filename
        self.xml_tree_callback      = xml_tree_callback
        self.add_aliases_to_analysis= add_aliases_to_analysis
        self.halt_on_exception      = halt_on_exception
        self.samplename_func        = samplename_func
        self.log_file               = None
        self.log_filename           = 'sframe_output.log'
        self.private_conf           = 'conf.xml'
        self.subprocess             = None

    def _push_aliases_to_analysis(self):
        if self.add_aliases_to_analysis:
            analysis.fs_aliases += self.result.wrps

    def prepare_run_conf(self):
        if self.xml_tree_callback:
            tree = ElementTree.parse(self.cfg_filename)
            self.xml_tree_callback(tree)
            with open(self.cfg_filename) as inp:
                dtd_header = inp.readline() + inp.readline()
            with open(os.path.join(self.cwd, self.private_conf), "w") as f:
                f.write(dtd_header + '\n')
                tree.write(f)
            # TODO make that nicer sometime...
            os.system('cp %s %s' % (
                os.path.dirname(self.cfg_filename) + '/JobConfig.dtd',
                self.cwd + '/JobConfig.dtd'
            ))
        else:
            self.private_conf = self.cfg_filename

    def make_result(self):
        def add_sample_name(w):
            w.sample = self.samplename_func(w)
            return w
        wrps = diskio.generate_aliases(self.cwd + '*.root')
        wrps = list(add_sample_name(w) for w in wrps)
        self.result = wrappers.WrapperWrapper(
            wrps,
            exit_code=self.subprocess.returncode,
            cwd=self.cwd,
            log_file=self.log_filename,
            conf_filename=self.private_conf,
        )
        self._push_aliases_to_analysis()

    def successful(self):
        return (
            self.subprocess
            and self.subprocess.returncode == 0
            and not settings.recieved_sigint
        )

    def finalize(self):
        err_msg = 'SFrame execution exited with error.'
        if self.subprocess:
            err_msg += ' (ret: %s)' % str(self.subprocess.returncode)
            if self.subprocess.returncode == 0 and self.log_file:
                self.log_file.close()
                self.log_file = None

        if self.log_file:
            self.log_file.close()
            self.log_file = None

        if self.successful():
            self.make_result()
        elif self.halt_on_exception or settings.recieved_sigint:
            raise RuntimeError(err_msg)
        else:
            self.message('WARNING ' + err_msg)

    def reuse(self):
        super(SFrame, self).reuse()
        self._push_aliases_to_analysis()

    def run(self):
        self.prepare_run_conf()

        log_path = os.path.join(self.cwd, self.log_filename)
        cmd = ['sframe_main', self.private_conf]
        self.log_file = open(log_path, "w")
        self.message('INFO Starting SFrame with command:')
        self.message('INFO `%s`' % " ".join(cmd))
        self.message(
            'INFO Follow with `tail -f %s`.'
            % os.path.abspath(log_path)
        )
        self.subprocess = subprocess.Popen(
            cmd,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            cwd=self.cwd,
        )
        while self.subprocess.returncode == None:
            self.subprocess.poll()
            time.sleep(1)

        self.finalize()
