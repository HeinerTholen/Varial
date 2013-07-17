
import settings
import monitor
import os
import time
import copy
import inspect

class PostProcBase(object):
    """
    Base class for post processing.
    """
    can_reuse = False
    has_output_dir = True

    def __init__(self, tool_name = None):
        super(PostProcBase, self).__init__()

        # name
        if not tool_name:
            self.name = self.__class__.__name__
        else:
            self.name = tool_name

        # messenger
        if not hasattr(self, "message"):
            self.message = monitor.Monitor().connect_object_with_messenger(self)

    def __enter__(self):
        settings.push_tool_dir(self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        settings.pop_tool_dir()

    def _reset(self):
        self.__init__(self.name)

    def wanna_reuse(self, all_reused_before_me):
        """Overwrite! If True is returned, run is not called."""
        return self.can_reuse and all_reused_before_me

    def starting(self):
        settings.create_folder(settings.dir_pstprc)
        if self.has_output_dir:
            settings.create_folder(settings.dir_result)
        self.messenger.started.emit()

    def run(self):
        """Overwrite!"""
        pass

    def finished(self):
        self.messenger.finished.emit()


class PostProcTool(PostProcBase):
    """"""
    can_reuse = True

    def __init__(self, name=None):
        super(PostProcTool, self).__init__(name)
        self.plot_output_dir = None
        self._info_file = None

    def __enter__(self):
        res = super(PostProcTool, self).__enter__()
        self.plot_output_dir = settings.dir_result
        self._info_file = os.path.join(settings.dir_pstprc, self.name)
        return res

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.plot_output_dir = None
        self._info_file = None
        super(PostProcTool, self).__exit__(exc_type, exc_val, exc_tb)

    def wanna_reuse(self, all_reused_before_me):
        if self.has_output_dir:
            output_dir_ok = os.path.exists(self.plot_output_dir)
        else:
            output_dir_ok = True
        return (
            super(PostProcTool, self).wanna_reuse(all_reused_before_me)
            and os.path.exists(self._info_file)
            and output_dir_ok
        )

    def starting(self):
        super(PostProcTool, self).starting()
        self.time_start = time.ctime() + "\n"
        if os.path.exists(self._info_file):
            os.remove(self._info_file)

    def finished(self):
        self.time_fin = time.ctime() + "\n"
        with open(self._info_file, "w") as f:
            f.write(self.time_start)
            f.write(self.time_fin)
        super(PostProcTool, self).finished()


class PostProcChain(PostProcBase):
    """
    Executes PostProcTools.
    """

    def __init__(self, name = None, tools = None):
        super(PostProcChain, self).__init__(name)
        self._reuse = False
        self.tool_chain = []
        if tools:
            self.add_tools(tools)

    def _reset(self):
        for t in self.tool_chain:
            t._reset()

    def add_tools(self, tools):
        for tool in tools:
            self.add_tool(tool)

    def add_tool(self, tool):
        assert (isinstance(tool, PostProcBase)
                or issubclass(tool, PostProcBase))
        if not isinstance(tool, PostProcBase):
            tool = tool()
        self.tool_chain.append(tool)

    def run(self):
        for tool in self.tool_chain:
            with tool as t:
                if tool.wanna_reuse(self._reuse):
                    tool.message("INFO Reusing last round's data. Skipping...")
                    continue
                elif tool.can_reuse:
                    self._reuse = False

                t._reuse = self._reuse
                t.starting()
                t.run()
                t.finished()
                self._reuse = t._reuse


class PostProcChainSystematics(PostProcChain):
    """Makes a deep copy of settings, restores on exit. Tools are reset."""
    def __enter__(self):
        res = super(PostProcChainSystematics, self).__enter__()
        old_settings_data = {}
        for key, val in settings.__dict__.iteritems():
            if not (
                key[:2] == "__"
                or key in settings.persistent_data
                or inspect.ismodule(val)
                or callable(val)
                ):
                try:
                    old_settings_data[key] = copy.deepcopy(val)
                except TypeError, e:
                    if not str(e) == "cannot deepcopy this pattern object":
                        raise
                    else:
                        self.message("WARNING Cannot deepcopy: " + key)
        self.old_settings_data = old_settings_data
        self.prepare_for_systematic()
        self.message("INFO Clearing settings.histopool and settings.post_proc_dict")
        del settings.histo_pool[:]
        settings.post_proc_dict.clear()
        return res

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish_with_systematic()
        settings.__dict__.update(self.old_settings_data)
        del self.old_settings_data
        self.after_restore()
        super(PostProcChainSystematics, self).__exit__(exc_type, exc_val,exc_tb)

    def starting(self):
        super(PostProcChainSystematics, self).starting()
        self.message("INFO Resetting tools.")
        self._reset()

    def prepare_for_systematic(self):
        """Overwrite!"""
        pass

    def finish_with_systematic(self):
        """Overwrite!"""
        pass

    def after_restore(self):
        """Overwrite!"""
        pass






