import glob
import itertools
import os
import shutil
import ROOT

import dbio
import generators as gen
import rendering
import settings

from toolinterface import Tool, ToolChain
from cmsrunproxy import CmsRunProxy
from fwliteproxy import FwliteProxy


class FSHistoLoader(Tool):
    io = dbio

    def __init__(self, name=None, filter_keyfunc=None):
        super(FSHistoLoader, self).__init__(name)
        self.filter_keyfunc = filter_keyfunc

    def run(self):
        self.result = list(gen.fs_filter_active_sort_load(self.filter_keyfunc))


class FSPlotter(Tool):
    """
    A plotter. Makes stacks and overlays data by default.

    Overriding set_up_content and setting self.stream_content lets
    Default attributes, that can be overwritten by init keywords:

    >>> defaults = {
    ...    'input_result_path': None,
    ...    'filter_keyfunc': None,
    ...    'hook_loaded_histos': None,
    ...    'hook_pre_canvas_build': None,
    ...    'hook_post_canvas_build': None,
    ...    'save_log_scale': False,
    ...    'save_lin_log_scale': False,
    ...    'keep_content_as_result': False,
    ...    'canvas_decorators': [
    ...        rendering.BottomPlotRatioSplitErr,
    ...        rendering.Legend
    ...    ]
    ...}
    """
    defaults_attrs = {
        'input_result_path': None,
        'filter_keyfunc': None,
        'hook_loaded_histos': None,
        'hook_pre_canvas_build': None,
        'hook_post_canvas_build': None,
        'save_log_scale': False,
        'save_lin_log_scale': False,
        'keep_content_as_result': False,
        'save_name_lambda': lambda wrp: wrp.name,
        'canvas_decorators': [
            rendering.BottomPlotRatioSplitErr,
            rendering.Legend
        ]
    }

    class NoFilterDictError(Exception):
        pass

    def __init__(self, name=None, **kws):
        super(FSPlotter, self).__init__(name)
        defaults = dict(self.defaults_attrs)
        defaults.update(self.__dict__)  # do not overwrite user stuff
        defaults.update(kws)            # add keywords
        self.__dict__.update(defaults)  # set attributes in place
        self.stream_content = None
        self.stream_canvas = None

    def configure(self):
        pass

    def load_content(self):
        if self.input_result_path:
            wrps = self.lookup(self.input_result_path)
            if not wrps:
                raise RuntimeError(
                    'ERROR Input not found: "%s"' % self.input_result_path)
        else:
            wrps = self.lookup('../FSHistoLoader')
        if wrps:
            if self.filter_keyfunc:
                wrps = itertools.ifilter(self.filter_keyfunc, wrps)
        else:
            if not self.filter_keyfunc:
                self.message("WARNING No filter_keyfunc set! "
                             "Working with _all_ histograms.")
            wrps = gen.fs_filter_active_sort_load(self.filter_keyfunc)
        if self.hook_loaded_histos:
            wrps = self.hook_loaded_histos(wrps)
        self.stream_content = wrps

    def set_up_content(self):
        wrps = self.stream_content

        # put TH2D's in one group each
        ungroupiter = iter(xrange(9999))
        wrps = gen.group(
            wrps,
            lambda w: w.analyzer+"_"+w.name+(
                "%03d" % next(ungroupiter)
                if isinstance(w.histo, ROOT.TH2D)
                else ""
            )
        )

        wrps = gen.mc_stack_n_data_sum(wrps, None, True)
        self.stream_content = wrps

    def store_content_as_result(self):
        if self.keep_content_as_result:
            self.stream_content = list(self.stream_content)
            self.result = list(
                itertools.chain.from_iterable(self.stream_content))

    def set_up_make_canvas(self):
        def put_ana_histo_name(grps):
            for grp in grps:
                grp.name = grp.renderers[0].analyzer+"_"+grp.name
                yield grp

        def run_build_procedure(bldr):
            for b in bldr:
                b.run_procedure()
                yield b

        def decorate(bldr):
            for b in bldr:
                if not isinstance(b.renderers[0].histo, ROOT.TH2D):
                    for dec in self.canvas_decorators:
                        b = dec(b)
                yield b
        bldr = gen.make_canvas_builder(self.stream_content)
        bldr = put_ana_histo_name(bldr)
        bldr = decorate(bldr)
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
        self.load_content()
        self.set_up_content()
        self.store_content_as_result()
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
        self.working_dir = working_dir
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
        if not self.working_dir:
            self.working_dir = os.path.join(*self.result_dir.split('/')[:-2])
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
            wrp = self.io.read(
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

    def run(self):
        """Run the single steps."""
        self.io.use_analysis_cwd = False
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
        self.io.use_analysis_cwd = True


class CopyTool(Tool):
    """Copy contents of a directory. Preserves .htaccess files."""
    def __init__(self, dest, src='',
                 ignore=("*.root", "*.pdf", "*.eps", "*.info"),
                 name=None):
        super(CopyTool, self).__init__(name)
        self.dest = dest
        self.src = src
        self.ignore = ignore

    def run(self):
        src = os.path.abspath(self.src or os.path.join(self.result_dir, '..'))
        dest = os.path.abspath(self.dest)

        # check for htaccess and copy it to src dirs
        htaccess = os.path.join(dest, '.htaccess')
        if os.path.exists(htaccess):
            for path, _, _ in os.walk(src):
                shutil.copy2(htaccess, path)

        # clean dest dir and copy
        shutil.rmtree(glob.glob(dest + '/*'), True)
        ign_pat = shutil.ignore_patterns(*self.ignore)
        for f in glob.glob(src + '/*'):
            shutil.copytree(
                os.path.join(src, f),
                os.path.join(dest, f),
                ignore=ign_pat
            )


class ZipTool(Tool):
    """Zip-compress a target."""
    def __init__(self, abs_path):
        super(ZipTool, self).__init__(None)
        self.abs_path = abs_path

    def run(self):
        p = os.path.join(settings.varial_working_dir, self.abs_path)
        os.system(
            'zip -r %s %s' % (p, p)
        )


