"""
Example use of the CmsAnalysisAC3B toolkit.
"""
import cmstoolsac3b.settings as settings
import cmstoolsac3b_example.settingsprofile_postproc # default color, legend names, ...
import cmstoolsac3b.postprocessing       # to build a tool
import cmstoolsac3b.generators as gen     # histogram stream processing
import cmstoolsac3b.rendering             # canvas decorators

class CrtlFiltStackPlotter(cmstoolsac3b.postprocessing.PostProcTool):
    """An cmstoolsac3b_example stack plotter with data overlay."""

    def run(self):
        """
        Load, stack, print and save histograms in a stream.
        """
        # combined operation for loading, filtering, stacking, etc..
        # the output looks like: [(stack1, data1), (stack2, data2), ...]
        stream_stack_n_data = gen.fs_mc_stack_n_data_sum(
            {
                "name"      : "histo",
                "analyzer"  : ["CrtlFiltEt", "CrtlFiltEta"]
            }
        )

        # plot (stack, data) pairs into canvases, with legend
        stream_canvas = gen.canvas(
            stream_stack_n_data,
            [cmstoolsac3b.rendering.Legend]
        )

        # store into dir of this tool
        stream_canvas = gen.save(
            stream_canvas,
            lambda wrp: self.plot_output_dir + wrp.name,  # this function returns a path without postfix
            settings.rootfile_postfixes
        )

        # pull everything through the stream
        count = gen.consume_n_count(stream_canvas)

        # make a nice statement
        self.message("INFO: "+self.name+" produced "+count+" canvases.")


# execute
import cmstoolsac3b_example.sampledefinition         # sample definitions, module goes into main
import cmstoolsac3b.main                 # for execution
if __name__ == '__main__':
    settings.cfg_main_import_path = "CmsPackage.CmsModule.doMyNonExistingAnalysis_cfg"
    cmstoolsac3b.main.main(
        samples=cmstoolsac3b_example.sampledefinition,
        post_proc_tool_classes=[CrtlFiltStackPlotter]
    )