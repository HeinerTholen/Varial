
import settings
import monitor
import os
import time

class PostProcTool(object):
    """
    Base class for post processing tool.

    A directory in <settings.DIR_PLOTS> with the class name of this tool is
    created. Messages can be printed with self.message().
    """
    can_reuse = True

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
        self._reuse = os.path.exists(self.plot_output_dir)
        monitor.Monitor().connect_object_with_messenger(self)

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
        self._reuse = all_processes_reused

    def add_tools(self, tools):
        for tool in tools:
            self.add_tool(tool)

    def add_tool(self, tool):
        assert (isinstance(tool, PostProcTool)
                or issubclass(tool, PostProcTool))
        if not isinstance(tool, PostProcTool):
            tool = tool()
        self.tool_chain.append(tool)

    def run(self):
        """All tools in tool chain are executed."""

        for tool in self.tool_chain:
            tool_info_file = os.path.join(
                settings.DIR_JOBINFO,
                tool.name
            )
            if tool.can_reuse and self._reuse:
                reuse = (os.path.exists(tool_info_file) and tool._reuse)
                reuse = tool.wanna_reuse(reuse)
                self._reuse = reuse
                if reuse:
                    tool.message("INFO Reusing last round's data. Skipping...")
                    continue

            if os.path.exists(tool_info_file):
                os.remove(tool_info_file)
            tool.messenger.started.emit()
            time_start = time.ctime() + "\n"
            tool.run()
            time_fin = time.ctime() + "\n"
            tool.messenger.finished.emit()
            with open(tool_info_file, "w") as f:
                f.write(time_start)
                f.write(time_fin)
