
import os
import time
import copy
import inspect
import settings
import wrappers
import diskio
import monitor


def deepish_copy(obj):
    if (
        isinstance(obj, type)
        or callable(obj)
        or inspect.ismodule(obj)
        or inspect.isclass(obj)
        or str(type(obj)) == "<type 'generator'>"
    ):
        return obj
    if type(obj) == list:
        return list(deepish_copy(o) for o in obj)
    if type(obj) == tuple:
        return tuple(deepish_copy(o) for o in obj)
    if type(obj) == dict:
        return dict((k, deepish_copy(v)) for k, v in obj.iteritems())
    if type(obj) == set:
        return set(deepish_copy(o) for o in obj)
    if hasattr(obj, "__dict__"):
        cp = copy.copy(obj)
        cp.__dict__.clear()
        for k, v in obj.__dict__.iteritems():
            cp.__dict__[k] = deepish_copy(v)
        return cp
    return obj


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
        self.message.started()

    def run(self):
        """Overwrite!"""
        pass

    def finished(self):
        self.message.finished()


class PostProcTool(PostProcBase):
    """"""
    can_reuse = True

    def __init__(self, name=None):
        super(PostProcTool, self).__init__(name)
        self.plot_output_dir = None
        self.result = None
        self._info_file = None
        self.time_start = None
        self.time_fin = None

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

    def reuse(self):
        self.message("INFO Reusing!")
        res_file = self.plot_output_dir + "result"
        if self.has_output_dir and os.path.exists(res_file+".info"):
            self.message("INFO Fetching last round's data: ")
            res = diskio.read(res_file)
            self.message(str(res))
            if hasattr(res, "RESULT_WRAPPERS"):
                self.result = list(diskio.read(f) for f in res.RESULT_WRAPPERS)
            else:
                self.result = res
            settings.post_proc_dict[self.name] = self.result

    def starting(self):
        super(PostProcTool, self).starting()
        self.time_start = time.ctime() + "\n"
        if os.path.exists(self._info_file):
            os.remove(self._info_file)

    def finished(self):
        res_file = self.plot_output_dir + "result"
        if isinstance(self.result, wrappers.Wrapper):
            self.result.name = self.name
            if self.has_output_dir:
                diskio.write(self.result, res_file)
            settings.post_proc_dict[self.name] = self.result
        elif isinstance(self.result, list) or isinstance(self.result, tuple):
            if self.has_output_dir:
                filenames = []
                for i, wrp in enumerate(self.result):
                    num_str = "_%03d" % i
                    wrp.name = self.name + num_str
                    filenames.append(res_file + num_str)
                    diskio.write(wrp, res_file + num_str)
                diskio.write(
                    wrappers.Wrapper(
                        name            = self.name,
                        RESULT_WRAPPERS = filenames
                    ),
                    res_file
                )
            settings.post_proc_dict[self.name] = self.result
        self.time_fin = time.ctime() + "\n"
        with open(self._info_file, "w") as f:
            f.write(self.time_start)
            f.write(self.time_fin)
        super(PostProcTool, self).finished()


#TODO: make option to rerun group if any if its tools must rerun.
class PostProcChain(PostProcBase):
    """Executes PostProcTools."""

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
                    tool.reuse()
                    continue
                elif tool.can_reuse:
                    self._reuse = False

                t._reuse = self._reuse
                t.starting()
                t.run()
                t.finished()
                self._reuse = t._reuse


class PostProcChainIndie(PostProcChain):
    """Same as chain, but always reuses."""

    def starting(self):
        super(PostProcChainIndie, self).starting()
        self._outer_reuse = self._reuse
        self._reuse = True

    def finished(self):
        self._reuse = self._outer_reuse
        del self._outer_reuse
        super(PostProcChainIndie, self).finished()


class PostProcChainVanilla(PostProcChain):
    """Makes a deep copy of settings, restores on exit. Tools are reset."""
    def __enter__(self):
        res = super(PostProcChainVanilla, self).__enter__()
        old_settings_data = {}
        for key, val in settings.__dict__.iteritems():
            if not (
                key[:2] == "__"
                or key in settings.persistent_data
                or inspect.ismodule(val)
                or callable(val)
            ):
                old_settings_data[key] = deepish_copy(val)
        self.old_settings_data = old_settings_data
        return res

    def __exit__(self, exc_type, exc_val, exc_tb):
        settings.__dict__.update(self.old_settings_data)
        del self.old_settings_data
        super(PostProcChainVanilla, self).__exit__(exc_type, exc_val,exc_tb)

    def starting(self):
        super(PostProcChainVanilla, self).starting()
        self.prepare_for_systematic()
        self.message("INFO Clearing settings.histopool and settings.post_proc_dict")
        del settings.histo_pool[:]
        settings.post_proc_dict.clear()
        self.message("INFO Resetting tools.")
        self._reset()

    def finished(self):
        self.finish_with_systematic()
        super(PostProcChainVanilla, self).finished()

    def prepare_for_systematic(self):
        """Overwrite!"""
        pass

    def finish_with_systematic(self):
        """Overwrite!"""
        pass






