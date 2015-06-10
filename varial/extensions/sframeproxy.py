"""
Host sframe processes in a toolchain.
"""

import xml.etree.cElementTree as ElementTree
import subprocess
import time
import os
join = os.path.join

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
                 name=None):
        super(SFrame, self).__init__(name)
        self.cfg_filename           = cfg_filename
        self.xml_tree_callback      = xml_tree_callback
        self.add_aliases_to_analysis= add_aliases_to_analysis
        self.halt_on_exception      = halt_on_exception
        self.log_file               = None
        self.log_filename           = 'sframe_output.log'
        self.private_conf           = 'conf.xml'
        self.subprocess             = None

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
        self.result = wrappers.WrapperWrapper(
            list(diskio.generate_aliases(self.cwd + '*.root')),
            exit_code=self.subprocess.returncode,
            cwd=self.cwd,
            log_file=self.log_filename,
            conf_filename=self.private_conf,
        )

        if self.add_aliases_to_analysis:
            analysis.fs_aliases += self.result.wrps

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
        if self.add_aliases_to_analysis:
            analysis.fs_aliases += self.result.wrps

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
