
import glob
import json
import subprocess
import time
import threading
import os

import monitor
import settings
import sample


class CmsRunProcess(object):
    """
    This class hosts a cmsRun process.
    cmsRun output is streamed into logfile.
    """

    def __init__(self, sample_inst, try_reuse_old_data=False, cfg_filename=None):
        super(CmsRunProcess, self).__init__()

        assert isinstance(sample_inst, sample.Sample)
        self.sample             = sample_inst
        self.name               = sample_inst.name
        self.cfg_filename       = settings.cfg_main_import_path
        if cfg_filename:
            self.cfg_filename = cfg_filename
        self.exe                = "cmsRun"
        self.log_filename       = settings.DIR_LOGS + sample_inst.name + ".log"
        self.conf_filename      = settings.DIR_CONFS + sample_inst.name + ".py"
        self.service_filename   = settings.DIR_FILESERVICE + sample_inst.name + ".root"
        self.jobinfo_filename   = settings.DIR_JOBINFO + sample_inst.name + ".ini"
        self.try_reuse_old_data = try_reuse_old_data
        self.will_reuse_data    = False
        self.reused_old_data    = False
        self.sig_int            = False
        self.subprocess         = None
        self.thread             = None
        self.callbacks_on_exit  = []
        self.time_start         = None
        self.time_end           = None
        self.message = monitor.connect_object_with_messenger(self)

    def __str__(self):
        return "CmsRunProcess(" + self.name + ")"

    def __repr__(self):
        return str(self)

    def prepare_run_conf(self):
        """
        Takes all infos about the cmsRun to be started and builds a configuration file
        with python code, which is passed to cmsRun on calling start(). Conf-file
        stored in settings.DIR_CONFS.
        """
        if self.try_reuse_old_data and self.check_reuse_possible():
            self.will_reuse_data = True
            return

        # collect lines to write out at once.
        conf_lines = [
            "# generated",
            "# on " + time.ctime(),
            "# by cmsrunprocess.py",
            ""
        ]

        # set __builtin__ variables
        smpl = self.sample
        builtin_dict = {
            "lumi"      : smpl.lumi,
            "is_data"   : smpl.is_data,
            "legend"    : smpl.legend,
            "sample"    : smpl.name
        }
        builtin_dict.update(settings.cfg_common_builtins)
        builtin_dict.update(smpl.cfg_builtin)

        conf_lines.append("import __builtin__")
        conf_lines.append("__builtin__.cms_var = " + repr(builtin_dict))
        conf_lines.append("")
        conf_lines.append("")

        # do import statement
        conf_lines.append("from " + self.cfg_filename + " import *")
        conf_lines.append("")

        # do input filename statements
        conf_lines.append("process.source.fileNames = [")
        for in_file in smpl.input_files:
            if in_file[:5] == "file:":
                files_in_dir = glob.glob(in_file[5:])
                if not files_in_dir:
                    self.message(
                        self,
                        "WARNING: no input files found for "+in_file[5:]
                    )
                for fid in files_in_dir:
                    conf_lines.append("    'file:" + fid + "',")
            else:
                conf_lines.append("    '" + in_file + "',")
        conf_lines.append("]")

        # do output filename statements
        if smpl.output_file:
            filename = smpl.output_file
            if filename[-5:] != ".root":
                filename += self.name + ".root"
            conf_lines.append(
                "process."
                + settings.cfg_output_module_name
                + ".fileName = '"
                + filename
                + "'"
            )

        # fileService statement
        if settings.cfg_use_file_service:
            conf_lines.append(
                "process.TFileService.fileName = '"
                + settings.DIR_FILESERVICE
                + smpl.name + ".root'"
            )
            conf_lines.append("")

        # custom code
        conf_lines += smpl.cfg_add_lines

        # write out file
        conf_file = open(self.conf_filename, "w")
        for line in conf_lines:
            conf_file.write(line + "\n")
        conf_file.close()

    def write_job_info(self, exit_code):
        """
        Writes start- and endtime as well as exitcode to the process info file
        in settings.DIR_JOBINFO.
        If self.sigint is true, it does not write anything.
        """
        self.time_end = time.ctime()

        # on SIGINT or reuse, do not write the process info
        if self.sig_int or self.reused_old_data:
            return

        # write out in json format
        with open(self.jobinfo_filename, "w") as info_file:
            json.dump(
                {
                    "startTime": self.time_start,
                    "endTime": self.time_end,
                    "exitCode": str(exit_code),
                },
                info_file
            )

    def check_reuse_possible(self):
        """
        Checks if log, conf and file service files are present and if the
        process was finished successfully before. If yes returns True,
        because the previous results can be used again.
        """
        if not os.path.exists(self.log_filename):
            return False
        if not os.path.exists(self.conf_filename):
            return False
        if (settings.cfg_use_file_service and
                not os.path.exists(self.service_filename)):
            return False
        if not os.path.exists(self.jobinfo_filename):
            return False
        with open(self.jobinfo_filename) as info_file:
            info = json.load(info_file)
            if type(info) == dict and not int(info.get("exitCode", 255)):
                return True

    def successful(self):
        return (self.time_end
                and self.subprocess.returncode == 0
                and not self.sig_int)

    def start(self):
        """
        Start cmsRun with conf-file. If self.try_reuse is True and reuse is
        possible, just calls 'cmsRun --help' and pipes output to /dev/null.
        """
        self.time_start = time.ctime()
        if self.will_reuse_data or settings.suppress_cmsRun_exec:
            self.reused_old_data = True
            if not settings.suppress_cmsRun_exec:
                self.message(self, "INFO reusing data for " + self.name)
            with open("/dev/null", "w") as logfile:
                self.subprocess = subprocess.Popen(["echo"], stdout=logfile)
        else:
            self.jobinfo.clear()
            self.jobinfo.sync()

            # python has no callback on exit, workaround with thread:
            def called_in_thread():
                with open(self.log_filename, "w") as logfile:
                    self.subprocess = subprocess.Popen(
                        [self.exe, self.conf_filename]+self.sample.cmsRun_args,
                        stdout=logfile,
                        stderr=subprocess.STDOUT
                    )
                    self.subprocess.wait()
                    for cb in self.callbacks_on_exit:
                        cb()
                    self.write_job_info(self.subprocess.returncode)

            self.thread = threading.Thread(target=called_in_thread)
            self.thread.start()

    def terminate(self):
        """
        Overwrites terminate method, set's flag for infofile first, then calls
        terminate.
        """
        self.sig_int = True
        self.subprocess.terminate()
