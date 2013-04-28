
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
        self.message = self.messenger.message.emit

    def _set_plot_output_dir(self):
        plot_output_dir = settings.DIR_PLOTS + self.name + "/"
        settings.tool_folders[self.name] = plot_output_dir
        self.plot_output_dir = plot_output_dir

    def __init__(self, tool_name = None):
        super(PostProcTool, self).__init__()

        if not tool_name:
            self.name = self.__class__.__name__
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

    def __init__(self, all_processes_reused):
        super(PostProcessor, self).__init__()
        self.reuse = all_processes_reused

    def add_tool(self, tool):
        reuse = tool.wanna_reuse(self.reuse)
        self.reuse = reuse
        tool.reuse = reuse
        self.tool_chain.append(tool)

    def run(self):
        """All tools in tool chain are executed."""
        for tool in self.tool_chain:
            if tool.reuse: continue
            tool.messenger.started.emit()
            tool.run()
            tool.messenger.finished.emit()
