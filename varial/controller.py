
import settings
import monitor
import cmsrunprocess as crp


class Controller(object):
    """Generates, starts and finishes cmsrunprocess instances."""

    def __init__(self):
        super(Controller, self).__init__()
        self.waiting_pros  = []
        self.running_pros  = []
        self.finished_pros = []
        self.failed_pros   = []
        self.callbacks_on_all_finished = []

        self.monitor = monitor.Monitor()
        self.monitor.connect_controller(self)
        settings.controller = self

    def setup_processes(self):
        """
        crp.CmsRunProcesses are set up, and filled into self.waiting_pros
        crp.CmsRunProcess.prepare_run_conf() is called for every process.
        """
        if self.waiting_pros:  # setup has been done already
            return

        for name, sample in settings.samples.iteritems():
            process = crp.CmsRunProcess(sample, settings.try_reuse_results)
            process.prepare_run_conf()
            settings.cmsRun_procs.append(process)
            if process.will_reuse_data:
                self.finished_pros.append(process)
            else:
                self.waiting_pros.append(process)
            self.monitor.proc_enqueued(process)

    def start_processes(self):
        """Starts the queued processes."""
        # check if launch is possible
        if len(self.waiting_pros) == 0:
            return
        if len(self.running_pros) >= settings.max_num_processes:
            return

        # start processing
        process = self.waiting_pros.pop(0)
        process.callbacks_on_exit.append(self.finish_processes)
        process.start()
        self.running_pros.append(process)
        self.monitor.proc_started(process)

        # recursively
        self.start_processes()

    def finish_processes(self):
        """Remove finished processes from self.running_pros."""
        for process in self.running_pros[:]:
            if process.time_end:
                self.running_pros.remove(process)
                if process.successful():
                    self.finished_pros.append(process)
                    self.monitor.proc_finished(process)
                else:
                    self.failed_pros.append(process)
                    self.monitor.proc_failed(process)

        # see if there is new processes to start
        self.start_processes()
        if not len(self.running_pros):
            for cb in self.callbacks_on_all_finished:
                cb()

    def abort_all_processes(self):
        self.waiting_pros = []
        for process in self.running_pros:
            process.terminate()
