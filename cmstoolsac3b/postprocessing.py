
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

    def __init__(self, tool_name = None):
        super(PostProcTool, self).__init__()

        if not tool_name:
            self.name = self.__class__.__name__
        else:
            self.name = tool_name
        self.plot_output_dir = settings.DIR_PLOTS
        self._set_plot_output_dir()
        self._reuse = os.path.exists(self.plot_output_dir)
        self._info_file = os.path.join(
            settings.DIR_JOBINFO,
            self.name
        )
        monitor.Monitor().connect_object_with_messenger(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _set_plot_output_dir(self):
        plot_output_dir = settings.DIR_PLOTS + self.name + "/"
        settings.tool_folders[self.name] = plot_output_dir
        self.plot_output_dir = plot_output_dir

    def wanna_reuse(self, all_reused_before_me):
        """Overwrite! If True is returned, run is not called."""
        return (self._reuse
                and all_reused_before_me
                and os.path.exists(self._info_file)
                )

    def starting(self):
        self.messenger.started.emit()
        self.time_start = time.ctime() + "\n"
        if os.path.exists(self._info_file):
            os.remove(self._info_file)

    def run(self):
        """Overwrite!"""
        pass

    def finished(self):
        self.time_fin = time.ctime() + "\n"
        with open(self._info_file, "w") as f:
            f.write(self.time_start)
            f.write(self.time_fin)
        self.messenger.finished.emit()


class PostProcToolChain(PostProcTool):
    """
    Executes PostProcTools.
    """
    can_reuse = False

    def __init__(self, name = None):
        super(PostProcToolChain, self).__init__(name)
        self._reuse = False
        self.tool_chain = []

    def _set_plot_output_dir(self):
        pass

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
        for tool in self.tool_chain:
            if tool.can_reuse:
                if tool.wanna_reuse(self._reuse):
                    tool.message("INFO Reusing last round's data. Skipping...")
                    continue
                else:
                    self._reuse = False

            with tool as t:
                t._reuse = self._reuse
                t.starting()
                t.run()
                t.finished()
                self._reuse = t._reuse

