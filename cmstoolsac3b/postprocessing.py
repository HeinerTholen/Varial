
import cmstoolsac3b.settings as settings
import cmstoolsac3b.monitor as mon
from PyQt4 import QtCore


class PostProcTool(object):
    """
    Base class for post processing tool.

    A directory in <settings.DIR_PLOTS> with the class name of this tool is
    created. Messages can be printed with self.message().
    """
    def __init__(self, ):
        super(PostProcTool, self).__init__()

        # plot output directory
        tool_name = self.__class__.__name__
        plot_output_dir = settings.DIR_PLOTS + tool_name + "/"
        settings.tool_folders[tool_name] = plot_output_dir
        self.name = tool_name
        self.plot_output_dir = plot_output_dir

        # qt message signals
        self.messenger = mon.Messenger()
        mon.Monitor().connect_object_with_messenger(self)
        self.message = self.messenger.message.emit

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
