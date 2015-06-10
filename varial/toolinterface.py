"""
Baseclasses for tools and toolchains.
"""

import multiprocessing.pool
import inspect
import signal
import time
import sys
import os

import analysis
import diskio
import monitor
import settings
import wrappers
from util import ResettableType, deepish_copy


class _ToolBase(object):
    """
    Base class for post processing.
    """
    can_reuse = False
    io = diskio

    def __init__(self, tool_name=None):
        super(_ToolBase, self).__init__()

        # name
        if not tool_name:
            self.name = self.__class__.__name__
        elif isinstance(tool_name, str):
            self.name = tool_name
        else:
            raise RuntimeError('tool_name must be string or None.')

        # messenger
        self.message = monitor.connect_object_with_messenger(self)

    def __enter__(self):
        analysis.push_tool(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        analysis.pop_tool()

    def reset(self):
        pass  # see metaclass

    def update(self):
        pass  # see metaclass

    def tool_paths(self):
        """Return a list of tool paths for all children."""
        raise RuntimeError('_ToolBase.tool_paths() should not be called.')

    def wanna_reuse(self, all_reused_before_me):
        """If True is returned, run() will not be called."""
        return self.can_reuse and all_reused_before_me

    def starting(self):
        self.message.started()

    def run(self):
        pass

    def finished(self):
        self.message.finished()

    @staticmethod
    def lookup_result(key, default=None):
        return analysis.lookup_result(key, default)


class Tool(_ToolBase):
    """Tool is the host for your business code."""
    __metaclass__ = ResettableType
    can_reuse = True

    def __init__(self, name=None):
        super(Tool, self).__init__(name)
        self.cwd = None
        self.result = None
        self.logfile = None
        self.logfile_res = None
        self.time_start = None
        self.time_fin = None

    def __enter__(self):
        if not self.time_fin:
            self.update()  # see metaclass
        else:
            self.reset()  # see metaclass
        res = super(Tool, self).__enter__()
        self.cwd = analysis.cwd
        self.logfile = os.path.join(
            self.cwd, '%s.log' % self.name)
        if self.can_reuse:
            self.logfile_res = os.path.join(
                self.cwd, '%s (result available).log' % self.name)
        else:
            self.logfile_res = self.logfile
        return res

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cwd = None
        self.logfile = None
        self.logfile_res = None
        super(Tool, self).__exit__(exc_type, exc_val, exc_tb)

    def tool_paths(self):
        """Return a list of tool paths for all children."""
        return [self.name]

    def wanna_reuse(self, all_reused_before_me):
        if super(Tool, self).wanna_reuse(all_reused_before_me):
            if os.path.exists(self.logfile):
                return True
            if (os.path.exists(self.logfile_res)
                and self.io.exists('result')):
                return True
        return False

    def reuse(self):
        self.message('INFO reusing...')
        with self.io.block_of_files:
            self.result = self.io.get('result')

    def starting(self):
        super(Tool, self).starting()
        self.time_start = time.ctime() + '\n'
        if os.path.exists(self.logfile):
            os.remove(self.logfile)
        if os.path.exists(self.logfile_res):
            os.remove(self.logfile_res)

    def finished(self):
        if any(isinstance(self.result, t) for t in (list, tuple)):
            try:
                self.result = wrappers.WrapperWrapper(self.result)
            except TypeError:
                pass
        if isinstance(self.result, wrappers.Wrapper):
            with self.io.block_of_files:
                self.result.name = self.name
                self.io.write(self.result, 'result')
        self.time_fin = time.ctime() + '\n'
        logfile = self.logfile_res if self.result else self.logfile
        with open(logfile, 'w') as f:
            f.write(self.time_start)
            f.write(self.time_fin)
        super(Tool, self).finished()


class ToolChain(_ToolBase):
    """Executes PostProcTools."""

    def __init__(self,
                 name=None,
                 tools=None,
                 default_reuse=False,
                 lazy_eval_tools_func=None):
        super(ToolChain, self).__init__(name)
        self._reuse = default_reuse
        self.tool_chain = []
        self.tool_names = {}
        self.lazy_eval_tools_func = lazy_eval_tools_func
        if tools:
            self.add_tools(tools)

    def reset(self):
        for t in self.tool_chain:
            t.reset()

    def add_tools(self, tools):
        for tool in tools:
            self.add_tool(tool)

    def add_tool(self, tool):
        if not isinstance(tool, _ToolBase):
            raise RuntimeError(
                '%s is not a subclass of Tool or ToolChain' % str(tool))
        if tool.name in self.tool_names:
            raise RuntimeError(
                'A tool named "%s" is already in this chain (%s).' % (
                    tool.name, self.name))
        self.tool_names[tool.name] = tool
        self.tool_chain.append(tool)

    def tool_paths(self):
        return list(os.path.join(self.name, p)
                    for t in self.tool_chain
                    for p in t.tool_paths())

    def _run_tool(self, tool):
        with tool as t:
            if tool.wanna_reuse(self._reuse):
                tool.reuse()
                return
            elif tool.can_reuse:
                if settings.only_reload_results:
                    monitor.reset()
                    raise RuntimeError('End of reload results mode at: ', t)
                self._reuse = False

            t._reuse = self._reuse
            t.starting()
            try:
                t.run()
            except:
                etype, evalue, etb = sys.exc_info()
                if not 'exception occured at path (class): ' in evalue.message:
                    evalue = etype(
                        '%s\nexception occured at path (class): %s (%s)' % (
                            evalue, analysis.cwd[:-1], t.__class__.__name__)
                    )
                raise etype, evalue, etb
            t.finished()
            self._reuse = t._reuse

    def run(self):
        if self.lazy_eval_tools_func:
            self.add_tools(self.lazy_eval_tools_func())
        for tool in self.tool_chain:
            self._run_tool(tool)


class ToolChainIndie(ToolChain):
    """Same as chain, but always reuses."""

    def starting(self):
        super(ToolChainIndie, self).starting()
        self._outer_reuse = self._reuse
        self._reuse = True

    def finished(self):
        self._reuse = self._outer_reuse
        del self._outer_reuse
        super(ToolChainIndie, self).finished()


class ToolChainVanilla(ToolChain):
    """
    Makes a deep copy of analysis module, restores on exit. Tools are reset.
    """
    def __enter__(self):
        res = super(ToolChainVanilla, self).__enter__()
        old_analysis_data = {}
        for key, val in analysis.__dict__.iteritems():
            if not (
                key[0] == '_'
                or key == 'results_base'    # must be kept for lookup
                or key == 'current_result'  # must be kept for lookup
                or inspect.ismodule(val)
                or callable(val)
            ):
                old_analysis_data[key] = deepish_copy(val)
            else:
                old_analysis_data[key] = val
        self._old_analysis_data = old_analysis_data
        return res

    def __exit__(self, exc_type, exc_val, exc_tb):
        analysis.__dict__.clear()
        analysis.__dict__.update(self._old_analysis_data)
        del self._old_analysis_data
        super(ToolChainVanilla, self).__exit__(exc_type, exc_val, exc_tb)

    def starting(self):
        super(ToolChainVanilla, self).starting()
        self.prepare_for_systematic()
        self.message('INFO Resetting tools.')
        self.reset()

    def finished(self):
        self.finish_with_systematic()
        super(ToolChainVanilla, self).finished()

    def prepare_for_systematic(self):
        pass

    def finish_with_systematic(self):
        pass


######################################################### ToolChainParallel ###
_n_parallel_workers = None
_n_parallel_workers_lock = None
_exception_lock = None  # exception printing should not be mingled
_kill_request = None  # initialized to 0, if > 0, the process group is killed


def _run_tool_in_worker(arg):
    chain_path, tool_index = arg
    chain = analysis.lookup_tool(chain_path)
    tool = chain.tool_chain[tool_index]
    try:
        chain._run_tool(tool)
    except KeyboardInterrupt:  # these will be handled from main process
        return tool.name, False, None
    except:  # print exception and request termination
        _exception_lock.acquire()
        if _kill_request.value == 0:
            print '='*80
            print 'EXCEPTION IN PARALLEL EXECUTION START'
            print '='*80
            import traceback
            traceback.print_exception(*sys.exc_info())
            print '='*80
            print 'EXCEPTION IN PARALLEL EXECUTION END'
            print '='*80
            _kill_request.value = 1
        _exception_lock.release()
        return tool.name, False
    return tool.name, chain._reuse


class _NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False
    def _set_daemon(self, value):
        pass
    daemon = property(_get_daemon, _set_daemon)

    def run(self):
        try:
            super(_NoDaemonProcess, self).run()
        except (KeyboardInterrupt, IOError):
            exit(-1)


class _NoDeamonWorkersPool(multiprocessing.pool.Pool):
    Process = _NoDaemonProcess


class ToolChainParallel(ToolChain):
    """Parallel execution of tools. Tools must not depend on each other."""
    def _load_results(self, tool):
        analysis.push_tool(tool)
        if isinstance(tool, Tool):
            tool.reuse()
        if isinstance(tool, ToolChain):
            if tool.lazy_eval_tools_func and not tool.tool_chain:
                tool.add_tools(tool.lazy_eval_tools_func())
            for t in tool.tool_chain:
                self._load_results(t)
        analysis.pop_tool()

    @staticmethod
    def _parallel_worker_start():
        if not _n_parallel_workers:
            return

        while _n_parallel_workers.value >= settings.max_num_processes:
            time.sleep(0.5)
        _n_parallel_workers_lock.acquire()
        _n_parallel_workers.value += 1
        _n_parallel_workers_lock.release()

    @staticmethod
    def _parallel_worker_done():
        if not _n_parallel_workers:
            return

        diskio.close_open_root_files()
        _n_parallel_workers_lock.acquire()
        _n_parallel_workers.value -= 1
        _n_parallel_workers_lock.release()

    def _run_tool(self, tool):
        if isinstance(tool, ToolChainParallel):
            super(ToolChainParallel, self)._run_tool(tool)
        else:
            self._parallel_worker_start()
            super(ToolChainParallel, self)._run_tool(tool)
            self._parallel_worker_done()

    def run(self):
        global _n_parallel_workers, \
            _n_parallel_workers_lock, \
            _exception_lock, \
            _kill_request

        if not settings.use_parallel_chains or settings.max_num_processes == 1:
            return super(ToolChainParallel, self).run()

        if self.lazy_eval_tools_func:
            self.add_tools(self.lazy_eval_tools_func())

        if not self.tool_chain:
            return

        # prepare parallelism (only once for the all processes)
        if not _n_parallel_workers:
            manager = multiprocessing.Manager()
            _n_parallel_workers = manager.Value('i', 0)
            _n_parallel_workers_lock = manager.Lock()
            _exception_lock = manager.Lock()
            _kill_request = manager.Value('i', 0)

        # prepare multiprocessing
        diskio.close_open_root_files()
        n_tools = len(self.tool_chain)
        my_path = "/".join(t.name for t in analysis._tool_stack)
        tool_index_list = list((my_path, i) for i in xrange(n_tools))
        pool = _NoDeamonWorkersPool(min(n_tools, settings.max_num_processes))
        result_iter = pool.imap_unordered(_run_tool_in_worker, tool_index_list)

        # run processing
        try:
            for name, reused in result_iter:
                if _kill_request.value > 0:
                    pool.close()
                    os.killpg(os.getpid(), signal.SIGTERM)  # one evil line!

                if not reused:
                    self._reuse = False

                err_level = monitor.current_error_level
                try:
                    monitor.current_error_level = 2
                    self._load_results(self.tool_names[name])
                finally:
                    monitor.current_error_level = err_level
        except KeyboardInterrupt:
            os.killpg(os.getpid(), signal.SIGTERM)  # again!

        # TODO: return results for ParallelToolChains in ParallelToolChains

        #cleanup
        pool.close()
        pool.join()
