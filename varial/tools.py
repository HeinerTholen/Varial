import itertools
import os
import shutil

import diskio
import generators as gen
import rendering
import settings

from toolinterface import Tool, ToolChain
from cmsrunprocess import CmsRunProxy
from fwliteproxy import FwliteProxy


# TODO: Make a new Plotter Interface with Composition:
# TODO: the functions should be non-class methods
class FSStackPlotter(Tool):
    """
    A 'stack with data overlay' plotter. Can be subclassed.

    Default attributes, that can be overwritten by init keywords:
    'filter_dict': dict
    'canvas_decorators': list
    'hook_loaded_histos': generator
    'hook_pre_canvas_build': generator
    'hook_post_canvas_build': generator,
    'save_log_scale': bool
    'save_lin_log_scale': bool
    """

    class NoFilterDictError(Exception):
        pass

    def __init__(self, name=None, **kws):
        super(FSStackPlotter, self).__init__(name)
        defaults = {
            'filter_dict': None,
            'hook_loaded_histos': None,
            'hook_pre_canvas_build': None,
            'hook_post_canvas_build': None,
            'save_log_scale': False,
            'save_lin_log_scale': False,
            'keep_stacks_as_result': False,
            'canvas_decorators': [
                rendering.BottomPlotRatioSplitErr,
                rendering.Legend
            ]
        }
        defaults.update(self.__dict__)  # do not overwrite user stuff
        defaults.update(kws)            # add keywords
        self.__dict__.update(defaults)  # set attributes in place
        self.save_name_lambda = lambda wrp: wrp.name

    def configure(self):
        pass

    def set_up_stacking(self):
        if not self.filter_dict:
            self.message("WARNING No filter_dict set! "
                         "Working with _all_ histograms.")
        wrps = gen.fs_filter_active_sort_load(self.filter_dict)
        if self.hook_loaded_histos:
            wrps = self.hook_loaded_histos(wrps)
        wrps = gen.group(wrps)
        wrps = gen.mc_stack_n_data_sum(wrps, None, True)
        if self. keep_stacks_as_result:
            self.stream_stack = list(wrps)
            self.result = list(itertools.chain.from_iterable(self.stream_stack))
        else:
            self.stream_stack = wrps

    def set_up_make_canvas(self):
        def put_ana_histo_name(grps):
            for grp in grps:
                grp.name = grp.renderers[0].analyzer+"_"+grp.name
                yield grp
        def run_build_procedure(bldr):
            for b in bldr:
                b.run_procedure()
                yield b
        bldr = gen.make_canvas_builder(self.stream_stack)
        bldr = put_ana_histo_name(bldr)
        bldr = gen.decorate(bldr, self.canvas_decorators)
        if self.hook_pre_canvas_build:
            bldr = self.hook_pre_canvas_build(bldr)
        bldr = run_build_procedure(bldr)
        if self.hook_post_canvas_build:
            bldr = self.hook_post_canvas_build(bldr)
        self.stream_canvas = gen.build_canvas(bldr)

    def set_up_save_canvas(self):
        if self.save_lin_log_scale:
            self.stream_canvas = gen.save_canvas_lin_log(
                self.stream_canvas,
                self.save_name_lambda,
            )
        else:
            if self.save_log_scale:
                self.stream_canvas = gen.switch_log_scale(self.stream_canvas)
            self.stream_canvas = gen.save(
                self.stream_canvas,
                self.save_name_lambda,
            )

    def run_sequence(self):
        count = gen.consume_n_count(self.stream_canvas)
        level = "INFO " if count else "WARNING "
        message = level+self.name+" produced "+str(count)+" canvases."
        self.message(message)

    def run(self):
        self.configure()
        self.set_up_stacking()
        self.set_up_make_canvas()
        self.set_up_save_canvas()
        self.run_sequence()


class SimpleWebCreator(Tool):
    """
    Browses through settings.DIR_PLOTS and generates webpages recursively for
    all directories.
    """

    def __init__(self, name=None, working_dir="", is_base=True):
        super(SimpleWebCreator, self).__init__(name)
        self.working_dir = working_dir or settings.varial_working_dir
        self.target_dir = settings.web_target_dir
        self.web_lines = []
        self.subfolders = []
        self.image_names = []
        self.plain_info = []
        self.plain_tex = []
        self.image_postfix = None
        self.is_base = is_base

    def configure(self):
        """A bit of initialization."""

        # get image format
        for pf in [".png", ".jpg", ".jpeg"]:
            if pf in settings.rootfile_postfixes:
                self.image_postfix = pf
                break
        if not self.image_postfix:
            self.message("ERROR No image formats for web available!")
            self.message("ERROR settings.rootfile_postfixes:"
                         + str(settings.rootfile_postfixes))
            self.message("ERROR html production aborted")
            return

        # collect folders and images
        for wd, dirs, files in os.walk(self.working_dir):
            self.subfolders += dirs
            for f in files:
                if f[-5:] == ".info":
                    if f[:-5] + self.image_postfix in files:
                        self.image_names.append(f[:-5])
                    else:
                        self.plain_info.append(f)
                if f[-4:] == ".tex":
                    self.plain_tex.append(f)
            break

    def go4subdirs(self):
        """Walk of subfolders and start instances. Remove empty dirs."""
        for sf in self.subfolders[:]:
            path = os.path.join(self.working_dir, sf)
            inst = self.__class__(self.name, path, False)
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
            '<body>',
            '<h2>'
            'DISCLAIMER: latest-super-preliminary-nightly'
            '-build-work-in-progress-analysis-snapshot'
            '</h2>'
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

    def make_info_file_divs(self):
        self.web_lines += ('<h2>Info files:</h2>',)
        for nfo in self.plain_info:
            wrp = diskio.read(
                os.path.join(self.working_dir, nfo)
            )
            self.web_lines += (
                '<div>',
                '<p>',
                '<b>' + nfo + '</b>',
                '<p>',
                '<pre>',
                str(wrp),
                '</pre>',
                '</div>',
                '<hr width="60%">',
            )

    def make_tex_file_divs(self):
        self.web_lines += ('<h2>Tex files:</h2>',)
        for tex in self.plain_tex:
            with open(os.path.join(self.working_dir, tex), "r") as f:
                self.web_lines += (
                    '<div>',
                    '<p>',
                    '<b>' + tex + '</b>',
                    '<p>',
                    '<pre>',
                )
                self.web_lines += f.readlines()
                self.web_lines += (
                    '</pre>',
                    '</div>',
                    '<hr width="60%">',
                )

    def make_image_divs(self):
        self.web_lines += ('<h2>Images:</h2>',)
        for img in self.image_names:
            #TODO get history from full wrapper!!
            history_lines = ""
            with open(os.path.join(self.working_dir,img + ".info")) as f:
                while f.next() != "\n":     # skip ahead to history
                    continue
                for line in f:
                    history_lines += line
            h_id = "history_" + img
            self.web_lines += (
                '<div>',
                '<p>',
                '<b>' + img + ':</b>',      # image headline
                '<a href="javascript:ToggleDiv(\'' + h_id
                + '\')">(toggle history)</a>',
                '</p>',
                '<div id="' + h_id          # history div
                + '" style="display:none;"><pre>',
                history_lines,
                '</pre></div>',
                '<img src="'                # the image itself
                + img + self.image_postfix
                + '" />',
                '</div>',
                '<hr width="95%">'
            )

    def finalize_page(self):
        self.web_lines += ["", "</body>", "</html>", ""]

    def write_page(self):
        """Write to disk."""
        for i, l in enumerate(self.web_lines):
            self.web_lines[i] += "\n"
        with open(os.path.join(self.working_dir, "index.html"), "w") as f:
            f.writelines(self.web_lines)

    def copy_page_to_destination(self):
        """Copies .htaccess to cwd. If on top, copies everything to target."""
        if not self.target_dir:
            return
        htaccess = os.path.join(self.target_dir, '.htaccess')
        if os.path.exists(htaccess):
            shutil.copy2(htaccess, self.working_dir)
        else:
            self.message("INFO Copying page to " + self.target_dir)
            shutil.copy2(os.path.join(self.working_dir, "index.html"),
                         self.target_dir)
            ign_pat = shutil.ignore_patterns(
                "*.root", "*.pdf", "*.eps", "*.info")
            for f in self.subfolders:
                shutil.rmtree(os.path.join(self.target_dir, f), True)
                shutil.copytree(
                    os.path.join(self.working_dir, f), 
                    os.path.join(self.target_dir, f),
                    ignore=ign_pat
                )

    def run(self):
        """Run the single steps."""
        diskio.use_analysis_cwd = False
        self.configure()
        if not self.image_postfix:
            return
        if self.image_names or self.subfolders or self.plain_info:
            self.message("INFO Building page in " + self.working_dir)
        else:
            return
        self.go4subdirs()
        self.make_html_head()
        self.make_headline()
        self.make_subfolder_links()
        self.make_info_file_divs()
        self.make_tex_file_divs()
        self.make_image_divs()
        self.finalize_page()
        self.write_page()
        if self.is_base:
            self.copy_page_to_destination()
        diskio.use_analysis_cwd = True
