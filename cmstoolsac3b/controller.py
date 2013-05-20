
from PyQt4 import QtCore
import settings
import monitor
import cmsrunprocess as crp

class Controller(QtCore.QObject):
    """Generates, starts and finishes crp.CmsRunProcesses."""
    process_enqueued  = QtCore.pyqtSignal(crp.CmsRunProcess)
    process_started   = QtCore.pyqtSignal(crp.CmsRunProcess)
    process_finished  = QtCore.pyqtSignal(crp.CmsRunProcess)
    process_failed    = QtCore.pyqtSignal(crp.CmsRunProcess)
    message           = QtCore.pyqtSignal(object, str)
    all_finished      = QtCore.pyqtSignal(list)

    def __init__(self):
        super(Controller, self).__init__()
        self.waiting_pros  = []
        self.running_pros  = []
        self.finished_pros = []
        self.failed_pros   = []

        mon = monitor.Monitor()
        mon.connect_controller(self)
        mon.message(
            self,
            "INFO: Using "
            + str(settings.max_num_processes)
            + " cpu cores at max."
        )

    def setup_processes(self):
        """
        crp.CmsRunProcesses are set up, and filled into self.waiting_pros
        crp.CmsRunProcess.prepare_run_conf() is called for every process.
        """
        if self.waiting_pros: #setup has been done already
            return

        for name, sample in settings.samples.iteritems():
            process = crp.CmsRunProcess(sample, settings.try_reuse_results)
            process.message.connect(self.message)
            process.prepare_run_conf()
            if process.will_reuse_data:
                self.finished_pros.append(process)
            else:
                self.waiting_pros.append(process)
            self.process_enqueued.emit(process)

    def start_processes(self):
        """Starts the queued processes."""
        # check if launch is possible
        if len(self.waiting_pros) == 0:
            return
        if len(self.running_pros) >= settings.max_num_processes:
            return

        # start processing
        process = self.waiting_pros.pop(0)
        process.finished.connect(self.finish_processes)
        process.start()
        self.running_pros.append(process)
        self.process_started.emit(process)

        # recursively
        self.start_processes()

    def finish_processes(self):
        """Remove finished processes from self.running_pros."""
        for process in self.running_pros[:]:
            if process.state() == 0:
                self.running_pros.remove(process)
                if process.exitCode() == 0:
                    self.finished_pros.append(process)
                    self.process_finished.emit(process)
                else:
                    self.failed_pros.append(process)
                    self.process_failed.emit(process)

        # see if there is new processes to start
        self.start_processes()
        if not len(self.running_pros):
            self.all_finished.emit(self.finished_pros)

    def abort_all_processes(self):
        self.waiting_pros = []
        for process in self.running_pros:
            process.terminate()
