"""
Example use of the CmsAnalysisAC3B toolkit.
"""
import settingsprofile_postproc               # default color, legend names, ...
from varial import settings
from varial import postprocessing             # to build a tool
from varial import generators as gen          # histogram stream processing
from varial import rendering                  # canvas decorators


class CrtlFiltStackPlotter(postprocessing.Tool):
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
            [rendering.Legend]
        )

        # store into dir of this tool
        stream_canvas = gen.save(
            stream_canvas,
            lambda wrp: self.result_dir + wrp.name,  # this function returns a path without postfix
            settings.rootfile_postfixes
        )

        # pull everything through the stream
        count = gen.consume_n_count(stream_canvas)

        # make a nice statement
        self.message("INFO: "+self.name+" produced "+count+" canvases.")


# execute
import sampledefinition     # sample definitions, module goes into main
import cmstoolsac3b.main    # for execution
if __name__ == '__main__':
    cmstoolsac3b.main.main(
        samples=sampledefinition,
        post_proc_tool_classes=[CrtlFiltStackPlotter],
        cfg_main_import_path="CmsPackage.CmsModule.doMyNonExistingAnalysis_cfg"
    )