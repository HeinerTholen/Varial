import settings
import postprocessing
import rendering
import generators as gen
import os


class FSStackPlotter(postprocessing.PostProcTool):
    """A 'stack with data overlay' plotter. To be subclassed."""

    class NoFilterDictError(Exception): pass

    def __init__(self, name = None):
        super(FSStackPlotter, self).__init__(name)
        if not hasattr(self, "filter_dict"):
            self.filter_dict = None
        if not hasattr(self, "canvas_decorators"):
            self.canvas_decorators = [
                rendering.BottomPlotRatio,
                rendering.LegendRight
            ]

    def configure(self):
        pass

    def set_up_stacking(self):
        if not self.filter_dict:
            raise self.NoFilterDictError(
                "filter_dict not set: subclass and overwrite configure()"
            )
        stream_stack = gen.fs_mc_stack_n_data_sum(self.filter_dict)
        self.stream_stack = gen.pool_store_items(stream_stack)

    def set_up_make_canvas(self):
        self.stream_canvas = gen.canvas(
            self.stream_stack,
            self.canvas_decorators
        )

    def set_up_save_canvas(self):
        self.stream_canvas = gen.save(
            self.stream_canvas,
            lambda wrp: self.plot_output_dir + wrp.name,
        )

    def run_sequence(self):
        count = gen.consume_n_count(self.stream_canvas)
        if count:
            level = "INFO "
        else:
            level = "WARNING "
        self.message(level+self.name+" produced "+str(count)+" canvases.")

    def run(self):
        self.configure()
        self.set_up_stacking()
        self.set_up_make_canvas()
        self.set_up_save_canvas()
        self.run_sequence()


class SimpleWebCreator(postprocessing.PostProcTool):
    """
    Browses through settings.DIR_PLOTS and generates webpages recursively for
    all directories.
    """

    def __init__(self, name = None):
        super(self.__class__, self).__init__(name)
        self.working_dir = ""
        self.web_lines = []
        self.subfolders = []
        self.image_names = []
        self.image_postfix = None

    def _set_plot_output_dir(self):
        pass

    def configure(self):
        """A bit of initialization."""
        if not self.working_dir:
            self.working_dir = settings.DIR_PLOTS

        # get image format
        for pf in [".png", ".jpg", ".jpeg"]:
            if pf in settings.rootfile_postfixes:
                self.image_postfix = pf
                break
        if not self.image_postfix:
            self.message("WARNING: No image formats for web available!")
            self.message("WARNING: settings.rootfile_postfixes:"
                         + str(settings.rootfile_postfixes))
            return

        # collect folders and images
        for wd, dirs, files in os.walk(self.working_dir):
            self.subfolders += dirs
            for f in files:
                if (f[-5:] == ".info" and
                    f[:-5] + self.image_postfix in files):
                    self.image_names.append(f[:-5])
            break

    def go4subdirs(self):
        """Walk of subfolders and start instances. Remove empty dirs."""
        for sf in self.subfolders[:]:
            path = os.path.join(self.working_dir, sf)
            inst = self.__class__()
            inst.working_dir = path
            inst.run()
            if not os.path.exists(os.path.join(path, "index.html")):
                self.subfolders.remove(sf)

    def make_html_head(self):
        self.web_lines += [
            '<html>',
            '<head>',
            '<script type="text/javascript" language="JavaScript"><!--',
            'function ToggleDiv(d) {',
            '  if(document.getElementById(d).style.display == "none") { ',
            '    document.getElementById(d).style.display = "block";',
            '  } else { ',
            '    document.getElementById(d).style.display = "none";',
            '  }',
            '}',
            '//--></script>',
            '</head>',
            '<body>'
        ]

    def make_headline(self):
        self.web_lines += (
            '<h1> Folder: ' + self.working_dir + '</h1>',
            '<hr width="60%">',
            ""
        )

    def make_subfolder_links(self):
        self.web_lines += ('<h2>Subfolders:</h2>',)
        for sf in self.subfolders:
            self.web_lines += (
                '<p><a href="'
                + os.path.join(sf, "index.html")
                + '">'
                + sf
                + '</a></p>',
            )
        self.web_lines += ('<hr width="60%">', "")

    def make_image_divs(self):
        self.web_lines += ('<h2>Images:</h2>',)
        for img in self.image_names:
            #TODO get history from full wrapper!!
            history_lines = ""
            with open(os.path.join(self.working_dir,img + ".info")) as f:
                f.next() #skip first two lines
                f.next() #skip first two lines
                for line in f:
                    history_lines += line
            h_id = "history_" + img
            self.web_lines += (
                '<div>',
                '<p>',
                '<b>' + img + ':</b>',     # image headline
                '<a href="javascript:ToggleDiv(\'' + h_id
                + '\')">(toggle history)</a>',
                '</p>',
                '<div id="' + h_id           # history div
                + '" style="display:none;"><pre>',
                history_lines,
                '</pre></div>',
                '<img src="'                 # the image itself
                + img + self.image_postfix
                + '" />',
                '</div>',
                '<hr width="95%">'
            )

    def finalize_page(self):
        self.web_lines += ["", "</body>", "</html>", ""]

    def write_page(self):
        """Write to disk."""
        for i,l in enumerate(self.web_lines):
            self.web_lines[i] += "\n"
        with open(os.path.join(self.working_dir, "index.html"), "w") as f:
            f.writelines(self.web_lines)

    def run(self):
        """Run the single steps."""
        self.configure()
        if not self.image_postfix: return # WARNING message above.
        if not (self.image_names or self.subfolders): return # Nothing to do
        self.go4subdirs()
        self.make_html_head()
        self.make_headline()
        self.make_subfolder_links()
        self.make_image_divs()
        self.finalize_page()
        self.write_page()

