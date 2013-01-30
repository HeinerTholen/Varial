
import settings
import postprocessing
import generators as gen
import rendering
import re

class StackPlotterFS(postprocessing.PostProcTool):
    """An cmstoolsac3b_example stack plotter with data overlay."""

    def __init__(self, name, histo_filter_dict):
        super(StackPlotterFS, self).__init__(name)
        self.histo_filter_dict = histo_filter_dict

    def run(self):
        """
        Load, stack, print and save histograms in a stream.
        """

        stream_stack = gen.fs_mc_stack_n_data_sum(
            {"analyzer":re.compile("CrtlFilt*")}
        )

        stream_stack = gen.pool_store_items(stream_stack)

        stream_stack = gen.debug_printer(stream_stack, False)

        stream_canvas = gen.canvas(
            stream_stack,
            #[rendering.Legend]
        )

        stream_canvas = gen.debug_printer(stream_canvas, False)

        stream_canvas = gen.save(
            stream_canvas,
            lambda wrp: self.plot_output_dir + wrp.name,
            settings.rootfile_postfixes
        )

        count = gen.consume_n_count(stream_canvas)
        self.message("INFO: "+self.name+" produced "+str(count)+" canvases.")

