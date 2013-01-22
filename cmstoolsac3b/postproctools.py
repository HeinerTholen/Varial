
import settings
import postprocessing
import generators as gen
import rendering

class StackPlotterFS(postprocessing.PostProcTool):
    """An cmstoolsac3b_example stack plotter with data overlay."""

    def __init__(self, name, histo_filter_dict):
        super(StackPlotterFS, self).__init__(name)
        self.histo_filter_dict = histo_filter_dict

    def run(self):
        """
        Load, stack, print and save histograms in a stream.
        """
        # combined operation for loading, filtering, stacking, etc..
        # the output looks like: [(stack1, data1), (stack2, data2), ...]
        stream_stack_n_data = gen.fs_mc_stack_n_data_sum(
            self.histo_filter_dict
        )

        # plot (stack, data) pairs into canvases, with legend
        stream_canvas = gen.canvas(
            stream_stack_n_data,
            [rendering.Legend]
        )

        # store into dir of this tool
        stream_canvas = gen.save(
            stream_canvas,
            lambda wrp: self.plot_output_dir + wrp.name,  # this function returns a path without postfix
            settings.rootfile_postfixes
        )

        # pull everything through the stream
        count = gen.consume_n_count(stream_canvas)

        # make a nice info statement
        self.message("INFO: "+self.name+" produced "+count+" canvases.")

