
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
        # the output looks like: [(stack1,), (stack2,), ...]
        stream_stack = gen.fs_mc_stack(
            self.histo_filter_dict
        )

        # plot (stack, data) pairs into canvases, with legend
        stream_canvas = gen.canvas(
            stream_stack,
            #[rendering.Legend],
            ana_histo_name = True,
        )

        def log_scale(wrps):
            for wrp in wrps:
                wrp.canvas.SetLogy()
                wrp.name += "_log"
                yield wrp
        stream_canvas = log_scale(stream_canvas)

        # store into dir of this tool
        stream_canvas = gen.save(
            stream_canvas,
            # this lambda function returns a path without postfix
            lambda wrp: self.plot_output_dir + wrp.name,
            settings.rootfile_postfixes
        )

        # pull everything through the stream
        count = gen.consume_n_count(stream_canvas)

        # make a nice info statement
        self.message("INFO: "+self.name+" produced "+str(count)+" canvases.")

