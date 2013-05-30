
import settings
import monitor
from PyQt4 import QtCore


class PostProcTool(object):
    """
    Base class for post processing tool.

    A directory in <settings.DIR_PLOTS> with the class name of this tool is
    created. Messages can be printed with self.message().
    """
    def _connect_message_signal(self):
        self.messenger = monitor.Messenger()
        monitor.Monitor().connect_object_with_messenger(self)

    def _set_plot_output_dir(self):
        plot_output_dir = settings.DIR_PLOTS + self.name + "/"
        settings.tool_folders[self.name] = plot_output_dir
        self.plot_output_dir = plot_output_dir

    def __init__(self, tool_name = None):
        super(PostProcTool, self).__init__()

        if not tool_name:
            self.name = self.__class__.__name__
        else:
            self.name = tool_name
        self.plot_output_dir = settings.DIR_PLOTS

        self._set_plot_output_dir()
        self._connect_message_signal()


    def wanna_reuse(self, all_reused_before_me):
        """Overwrite! If True is returned, run is not called."""
        return False

    def run(self):
        """Overwrite!"""
        pass


class PostProcessor(object):
    """
    Executes PostProcTools.
    """
    tool_chain = []
    reuse = False
    messanger = monitor.Messenger()

    def __init__(self, all_processes_reused):
        super(PostProcessor, self).__init__()
        self.reuse = all_processes_reused
        self.messenger = monitor.Messenger()
        monitor.Monitor().connect_object_with_messenger(self)

    def add_tools(self, tools):
        for tool in tools:
            self.add_tool(tool)

    def add_tool(self, tool):
        assert (isinstance(tool, PostProcTool)
                or issubclass(tool, PostProcTool))
        if not isinstance(tool, PostProcTool):
            tool = tool()
        self.reuse = tool.wanna_reuse(self.reuse)
        tool.reuse = self.reuse
        self.tool_chain.append(tool)

    def remove_non_finished_samples(self, finished_procs):
        finished_procs = map(lambda x: x.name, finished_procs)
        for sample in settings.samples.keys():
            if not sample in finished_procs:
                self.message(
                    "WARNING: Process '"
                    + sample
                    + "' unfinished. Removing sample from list."
                )
                del settings.samples[sample]

    def run(self, finished_procs = None):
        """All tools in tool chain are executed."""
        if finished_procs:
            self.remove_non_finished_samples(finished_procs)

        for tool in self.tool_chain:
            if tool.reuse: continue
            tool.messenger.started.emit()
            tool.run()
            tool.messenger.finished.emit()
