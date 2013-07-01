
import settings
import monitor
import os
import time
import copy
import inspect

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
            settings.DIR_PSTPRCINFO,
            self.name
        )
        monitor.Monitor().connect_object_with_messenger(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _set_plot_output_dir(self):
        self.plot_output_dir = settings.DIR_PLOTS + self.name + "/"

    def wanna_reuse(self, all_reused_before_me):
        """Overwrite! If True is returned, run is not called."""
        return (self._reuse
                and all_reused_before_me
                and os.path.exists(self._info_file)
                )

    def starting(self):
        settings.tool_folders[self.name] = self.plot_output_dir
        settings.create_folders()
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


class PostProcChain(PostProcTool):
    """
    Executes PostProcTools.
    """
    can_reuse = False

    def __init__(self, name = None, tools = None):
        super(PostProcChain, self).__init__(name)
        self._reuse = False
        if not hasattr(self, "tool_chain"):
            self.tool_chain = []
        if tools:
            self.add_tools(tools)

    def add_tools(self, tools):
        for tool in tools:
            self.add_tool(tool)

    def add_tool(self, tool):
        assert (isinstance(tool, PostProcTool)
                or issubclass(tool, PostProcTool))
        if not isinstance(tool, PostProcTool):
            tool = tool()
        self.tool_chain.append(tool)

    def starting(self):
        self.old_PSTPRCINFO = settings.DIR_PSTPRCINFO
        self.old_PLOTS = settings.DIR_PLOTS
        settings.DIR_PSTPRCINFO += self.name + "/"
        settings.DIR_PLOTS += self.name + "/"
        for tool in self.tool_chain:
            tool.__init__(tool.name)
        self._info_file = os.path.join(
            settings.DIR_PSTPRCINFO,
            self.name
        )
        super(PostProcChain, self).starting()

    def finished(self):
        super(PostProcChain, self).finished()
        settings.DIR_PSTPRCINFO = self.old_PSTPRCINFO
        settings.DIR_PLOTS = self.old_PLOTS

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


class PostProcChainSystematics(PostProcChain):
    """Makes a shallow copy of settings, restores on exit."""
    def __enter__(self):
        old_settings_data = {}
        for key, val in settings.__dict__.iteritems():
            if not (
                key[:2] == "__"
                or key == "gROOT"
                or key == "persistent_dict"
                or inspect.ismodule(val)
                or callable(val)
                ):
                old_settings_data[key] = copy.copy(val)
        self.old_settings_data = old_settings_data
        self.message("INFO Clearing settings.histopool")
        del settings.histo_pool[:]
        self.prepare_for_systematic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish_with_systematic()
        settings.__dict__.update(self.old_settings_data)
        del self.old_settings_data
        self.after_restore()

    def prepare_for_systematic(self):
        """Overwrite!"""
        pass

    def finish_with_systematic(self):
        """Overwrite!"""
        pass

    def after_restore(self):
        """Overwrite!"""
        pass






