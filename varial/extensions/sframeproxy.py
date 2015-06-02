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
from varial import settings
from varial import toolinterface
from varial import wrappers


class SFrameProcess(toolinterface.Tool):
    """
    This class hosts a sframe process.

    sframe output is streamed into a logfile.
    """

    def __init__(self,
                 cfg_filename,
                 xml_tree_callback=None,
                 add_aliases_to_analysis=True,
                 name=None):
        super(SFrameProcess, self).__init__(name)
        self.cfg_filename           = cfg_filename
        self.xml_tree_callback      = xml_tree_callback
        self.add_aliases_to_analysis= add_aliases_to_analysis
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
        self.private_conf = self.cfg_filename


    def make_result(self):
        if settings.recieved_sigint:
            return

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
            self.time_fin
            and self.subprocess.returncode == 0
            and not settings.recieved_sigint
        )

    def finalize(self):
        if self.subprocess:
            if self.subprocess.returncode == 0 and self.log_file:
                self.log_file.close()
                self.log_file = None
                # TODO: find way to check for sframe error message
                #with open(self.log_filename, "r") as f:
                #    if 'Exception ------' in "".join(f.readlines()):
                #        self.subprocess.returncode = -1
        if self.log_file:
            self.log_file.close()
            self.log_file = None
            self.make_result()

    def run(self):
        self.prepare_run_conf()

        self.log_file = open(os.path.join(self.cwd, self.log_filename), "w")
        self.subprocess = subprocess.Popen(
            ["sframe_main", self.private_conf],
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            cwd=self.cwd,
        )
        while self.subprocess.returncode == None:
            self.subprocess.poll()
            time.sleep(1)

        self.finalize()


#class SFrameProxy(toolinterface.Tool):
#    """
#    Tool to embed sframe execution into varial toolchains.
#
#    For every job, a seperate xml config is writen, that mirrors the given
#    main config file.
#
#    :param cfg_filename:        str, path to cmsRun-config,
#                                e.g. `MySubSystem.MyPackage.config_cfg'`
#    :param use_file_service:    bool, fileservice in CMSSW config?
#                                default: ``True``
#    :param output_module_name:  str, name of output module in CMSSW config
#                                default: ``out``
#    :param common_builtings:    dict, write to ``__builtin__`` section of the
#                                config
#                                default: ``None``
#    :param name:                str, tool name
#    """
#    def __init__(self,
#                 cfg_filename,
#                 use_file_service=True,
#                 output_module_name="out",
#                 common_builtins=None,
#                 name=None):
#        super(SFrameProxy, self).__init__(name)
#        self.waiting_pros = []
#        self.running_pros = []
#        self.finished_pros = []
#        self.failed_pros = []
#        self.cfg_filename = cfg_filename
#        self.use_file_service = use_file_service
#        self.output_module_name = output_module_name
#        self.common_builtins = common_builtins or {}
#        self.try_reuse = settings.try_reuse_results
#
#    def wanna_reuse(self, all_reused_before_me):
#        self._setup_processes()
#
#        if settings.only_reload_results:
#            return True
#
#        return not bool(self.waiting_pros)
#
#    def reuse(self):
#        super(SFrameProxy, self).reuse()
#        self._finalize()
#
#    def run(self):
#        if settings.suppress_eventloop_exec:
#            self.message(
#                self, "INFO settings.suppress_eventloop_exec == True, pass...")
#            return
#
#        # TODO do sframe compilation
#
#        if not (settings.not_ask_execute or raw_input(
#                "Really run these cmsRun jobs:\n   "
#                + ",\n   ".join(map(str, self.waiting_pros))
#                + ('\nusing %i cores' % settings.max_num_processes)
#                + "\n?? (type 'yes') "
#                ) == "yes"):
#            return
#
#        self._handle_processes()
#        sig_term_sent = False
#        while self.running_pros:
#            if settings.recieved_sigint and not sig_term_sent:
#                self.abort_all_processes()
#                sig_term_sent = True
#            time.sleep(0.2)
#            self._handle_processes()
#
#        self.result = wrappers.Wrapper(
#            finished_procs=list(p.name for p in self.finished_pros))
#        self._finalize()
#
#    def _setup_processes(self):
#        for d in ('logs', 'confs', 'fs', 'report'):
#            path = join(self.cwd, d)
#            if not os.path.exists(path):
#                os.mkdir(path)
#
#        for name, smpl in analysis.all_samples.iteritems():
#            process = SFrameProcess(smpl, self.try_reuse, self.cfg_filename)
#            if process.check_reuse_possible(self.use_file_service):
#                self.finished_pros.append(process)
#            else:
#                self.waiting_pros.append(process)
#                monitor.proc_enqueued(process)
#
#    def _handle_processes(self):
#        # start processing
#        if (len(self.running_pros) < settings.max_num_processes
#                and self.waiting_pros):
#            process = self.waiting_pros.pop(0)
#            process.prepare_run_conf(
#                self.use_file_service,
#                self.output_module_name,
#                self.common_builtins
#            )
#            process.start()
#            monitor.proc_started(process)
#            self.running_pros.append(process)
#
#        # finish processes
#        for process in self.running_pros[:]:
#            process.subprocess.poll()
#            if None == process.subprocess.returncode:
#                continue
#
#            self.running_pros.remove(process)
#            process.finalize()
#            if process.successful():
#                self.finished_pros.append(process)
#                monitor.proc_finished(process)
#            else:
#                self.failed_pros.append(process)
#                monitor.proc_failed(process)
#
#    def _finalize(self):
#        if settings.recieved_sigint:
#            return
#        if not self.use_file_service:
#            return
#        for process in self.finished_pros:
#            analysis.fs_aliases += list(
#                alias for alias in diskio.generate_fs_aliases(
#                    process.service_filename,
#                    process.sample
#                )
#            )
#
#    def abort_all_processes(self):
#        self.waiting_pros = []
#        for process in self.running_pros:
#            process.terminate()
