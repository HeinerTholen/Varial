"""
Post processing tools that can be used nearly out-of-the-box.
"""


from varial import generators as gen     # histogram stream processing
from varial import postprocessing        # base class for post processing
import itertools                         # very useful!!

class StackPlusDataPlotter(postprocessing.Tool):
    """
    Subclass me and feed the data members!
    """
    store_stack_and_data_in_pool    = False #: Set True to drop all stacks and histos into the pool.
    canvas_decorators               = []    #: Give Decorators for the canvas builder.
    canvas_callback                 = None  #: Callback function, called with CanvasBuilders before execution.
    histo_filter_dict               = {}    #: Filter dict. see histotools.generators.filter for specification.

    def wanna_reuse(self, all_reused_before_me):
        """
        In this method one can check, if data from last time running is still
        available. If yes is returned, then run() is not called.
        """
        # simply believe, that the products of this tool did not change, when
        # nothing changed before:
        # caution: if this module fills the histopool, these histos are missing!
        return all_reused_before_me

    def store_to_pool(self, stream_stack_n_data):
        """
        Keep stacks and data histograms in histopool, for later use.
        The stream has to be splitted in a stack and a data stream and to be
        rejoined in the end.
        """
        stream_stack_n_data        = itertools.chain(stream_stack_n_data)   # resolve grouping
        stream_data, stream_stacks = gen.split_data_mc(stream_stack_n_data) # split (stacks are mc)
        stream_stacks              = gen.pool_store_items(stream_stacks)    # store
        stream_data                = gen.pool_store_items(stream_data)      # store
        stream_stack_n_data        = itertools.izip(stream_stacks, stream_data) # join stream again
        return stream_stack_n_data

    def run(self):
        """
        Load, stack, print and save histograms in a stream.
        """
        # combined operation for loading, filtering, stacking, etc..
        # the output looks like: [(stack1, data1), (stack2, data2), ...]
        stream_stack_n_data = gen.fs_mc_stack_n_data_sum(
            self.histo_filter_dict
        )

        # can be saved for later use.
        if self.store_stack_and_data_in_pool:
            stream_stack_n_data = self.store_to_pool(stream_stack_n_data)

        # plot (stack, data) pairs into canvases, with decorators
        stream_canvas = gen.canvas(
            stream_stack_n_data,
            self.canvas_decorators
        )

        # store into dir of this tool
        stream_canvas = gen.save(
            stream_canvas,
            lambda wrp: self.result_dir + wrp.analyzer
        )

        # pull everything through the stream
        count = gen.consume_n_count(stream_canvas)

        # make a nice statement
        self.message("INFO: "+self.name+" produced "+count+" canvases.")

