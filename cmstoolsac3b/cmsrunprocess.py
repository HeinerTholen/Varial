import time
import os
import glob
import cmstoolsac3b.settings as settings
import cmstoolsac3b.sample
from PyQt4 import QtCore

class CmsRunProcess(QtCore.QProcess):
    """
    This class hosts a cmsRun process.
    cmsRun output is streamed into logfile.
    """
    message = QtCore.pyqtSignal(object, str)

    def __init__(self, sample, try_reuse_old_data = False, cfg_filename=None):
        super(CmsRunProcess, self).__init__()

        assert isinstance(sample, cmstoolsac3b.sample.Sample)
        self.sample             = sample
        self.name               = sample.name
        self.cfg_filename       = settings.cfg_main_import_path
        if cfg_filename: self.cfg_filename = cfg_filename
        self.exe                = "cmsRun"
        self.log_filename       = settings.DIR_LOGS\
                                  + "/" + sample.name + ".log"
        self.conf_filename      = settings.DIR_CONFS\
                                  + "/" + sample.name + ".py"
        self.service_filename   = settings.DIR_FILESERVICE\
                                  + "/" + sample.name + ".root"
        self.jobinfo_filename   = settings.DIR_JOBINFO + "/" + sample.name + ".ini"
        self.jobinfo            = QtCore.QSettings(self.jobinfo_filename, 1)
        self.try_reuse_old_data = try_reuse_old_data
        self.will_reuse_data    = False
        self.reused_old_data    = False
        self.sig_int            = False

        # set all environment
        self.setWorkingDirectory(os.getcwd())
        self.setEnvironment(QtCore.QProcess.systemEnvironment())
        self.setProcessChannelMode(1)
        self.setStandardOutputFile(self.log_filename)
        self.finished.connect(self.write_job_info)

    def __str__(self):
        return "CmsRunProcess(" + self.name + ")"

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
        sample = self.sample
        builtin_dict = {
            "lumi": sample.lumi,
            "isData": sample.is_data,
            "legend": sample.legend,
            "sample": '"' + sample.name + '"'
        }
        builtin_dict.update(self.sample)
        builtin_dict.update(settings.cfg_common_builtins)

        conf_lines.append("import __builtin__")
        conf_lines.append("__builtin__.cms_var = " + repr(builtin_dict))
        conf_lines.append("")
        conf_lines.append("")

        # do import statement
        conf_lines.append("from " + self.cfg_filename + " import *")
        conf_lines.append("")

        # do input filename statements
        conf_lines.append("process.source.fileNames = [")
        for in_file in sample.input_files:
            if in_file[:5] == "file:":
                files_in_dir = glob.glob(in_file[5:])
                for fid in files_in_dir:
                    conf_lines.append("    'file:" + fid + "',")
            else:
                conf_lines.append("    '" + in_file + "',")
        conf_lines.append("]")

        # do output filename statements
        if sample.output_file:
            filename = sample.output_file
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
                + settings.DIR_FILESERVICE + "/"
                + sample.name + ".root'"
            )
            conf_lines.append("")

        # custom code
        conf_lines += sample.cfg_add_lines

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

        # collect lines to be written at once TODO: pythonify
        job_info = QtCore.QSettings(self.jobinfo_filename, 1)
        job_info.setValue("startTime", self.time_start)
        job_info.setValue("endTime", self.time_end)
        job_info.setValue("exitCode", str(exit_code))
        job_info.sync()

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
        if not os.path.exists(self.service_filename):
            return False
        if not os.path.exists(self.jobinfo_filename):
            return False
        prev_exit_code, parse_ok = self.jobinfo.value("exitCode", 255).toInt()
        return parse_ok and not prev_exit_code

    def start(self):
        """
        Start cmsRun with conf-file. If self.try_reuse is True and reuse is
        possible, just calls 'cmsRun --help' and pipes output to /dev/null.
        """
        self.time_start =  time.ctime()
        if self.will_reuse_data or settings.suppress_cmsRun_exec:
            self.setStandardOutputFile("/dev/null")
            self.reused_old_data = True
            if not settings.suppress_cmsRun_exec: #TODO too complicated!!
                self.message.emit(self, "INFO reusing data for " + self.name)
            super(CmsRunProcess, self).start(self.exe, ["--help"])
        else:
            self.jobinfo.clear()
            self.jobinfo.sync()
            super(CmsRunProcess, self).start(self.exe, [self.conf_filename])

    def terminate(self):
        """
        Overwrites terminate method, set's flag for infofile first, then calls
        terminate.
        """
        self.sig_int = True
        super(CmsRunProcess,self).terminate()
