import os

import analysis
import diskio
import settings
import toolinterface
import wrappers


class WebCreator(toolinterface.Tool):
    """
    Generates webpages for all directories.

    WebCreator instanciates itself recursively for every directory.

    :param name:            str, tool name
    :param working_dir:     str, directory to start with.
    :param is_base:         bool, **Do not touch! =)**
    """

    def __init__(self, name=None, working_dir='', is_base=True):
        super(WebCreator, self).__init__(name)
        self.working_dir = working_dir
        self.web_lines = []
        self.subfolders = []
        self.image_names = []
        self.plain_info = []
        self.plain_tex = []
        self.image_postfix = None
        self.is_base = is_base

    def configure(self):
        # get image format
        for pf in ['.png', '.jpg', '.jpeg']:
            if pf in settings.rootfile_postfixes:
                self.image_postfix = pf
                break
        if not self.image_postfix:
            self.message('ERROR No image formats for web available!')
            self.message('ERROR settings.rootfile_postfixes:'
                         + str(settings.rootfile_postfixes))
            self.message('ERROR html production aborted')
            return

        # collect folders and images
        if not self.working_dir:
            if self.cwd:
                self.working_dir = os.path.join(*self.cwd.split('/')[:-2])
            else:
                self.working_dir = analysis.cwd
        for wd, dirs, files in os.walk(self.working_dir):
            self.subfolders += dirs
            for f in files:
                if f[-5:] == '.info':
                    if f[:-5] + self.image_postfix in files:
                        self.image_names.append(f[:-5])
                    else:
                        self.plain_info.append(f)
                if f[-4:] == '.tex':
                    self.plain_tex.append(f)
            break

    def go4subdirs(self):
        for sf in self.subfolders[:]:
            path = os.path.join(self.working_dir, sf)
            inst = self.__class__(self.name, path, False)
            inst.run()
            if not os.path.exists(os.path.join(path, 'index.html')):
                self.subfolders.remove(sf)

    def make_html_head(self):
        self.web_lines += [
            '<html>',
            '<head>',
            '<title>',
            self.name + ': ' + self.working_dir,
            '</title>',
            '<style type="text/css">',
            'body {font-family: Helvetica, Verdana, Arial, "sans-serif"; }',
            '</style>',
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
            '<h2>',
            'DISCLAIMER: This page contains an intermediate analysis-snapshot!',
            '</h2>',
        ]

    def make_headline(self):
        breadcrumb = list(d1 for d1 in self.working_dir.split('/') if d1)
        n_folders = len(breadcrumb) - 1
        self.web_lines += (
            '<h1> Folder: ',
        ) + tuple(
            '<a href="%sindex.html">%s</a> / ' % ('../'*(n_folders-i), d)
            for i, d in enumerate(breadcrumb)
        ) + (
            '</h1>',
            '<hr width="60%">',
            ''
        )

    def make_subfolder_links(self):
        if not self.subfolders:
            return
        self.web_lines += ('<h2>Subfolders:</h2>',)
        for sf in self.subfolders:
            self.web_lines += (
                '<p><a href="'
                + os.path.join(sf, 'index.html')
                + '">'
                + sf
                + '</a></p>',
            )
        self.web_lines += ('<hr width="60%">', '')

    def make_info_file_divs(self):
        if not self.plain_info:
            return
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
        if not self.plain_tex:
            return
        self.web_lines += ('<h2>Tex files:</h2>',)
        for tex in self.plain_tex:
            with open(os.path.join(self.working_dir, tex), 'r') as f:
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
        if not self.image_names:
            return

        # headline / toc
        self.web_lines += (
            '<a name="toc"></a>',
            '<h2>Images:</h2>',
            '<div><p>',
        ) + tuple(
            '<a href="#%s">%s</a></br>' % (img, img)
            for img in self.image_names
        ) + (
            '</p></div>',
        )

        # images
        for img in self.image_names:
            with open(os.path.join(self.working_dir, img + '.info')) as f:
                wrp = wrappers.Wrapper(**diskio._read_wrapper_info(f))
                del wrp.history
                info_lines = wrp.pretty_writeable_lines()
                history_lines = ''.join(f)
            i_id = 'info_' + img
            h_id = 'history_' + img
            self.web_lines += (
                '<div>',
                '<p>',
                ('<a name="%s">' % img),                    # anchor
                '<b>' + img + ':</b></br>',                 # image headline
                '<a href="javascript:ToggleDiv(\'' + h_id   # toggle history
                + '\')">(toggle history)</a>',
                '<a href="javascript:ToggleDiv(\'' + i_id   # toggle info
                + '\')">(toggle info)</a>',
                '<a href="#toc">(back to top)</a>',
                '</p>',
                '<div id="' + h_id                          # history div
                + '" style="display:none;"><pre>',
                history_lines,
                '</pre></div>',
                '<div id="' + i_id                          # info div
                + '" style="display:none;"><pre>',
                info_lines,
                '</pre></div>',
                '<img src="'                                # the image itself
                + img + self.image_postfix
                + '" />',
                '</div>',
                '<hr width="95%">'
            )

    def finalize_page(self):
        self.web_lines += ['', '</body>', '</html>', '']

    def write_page(self):
        for i, l in enumerate(self.web_lines):
            self.web_lines[i] += '\n'
        with open(os.path.join(self.working_dir, 'index.html'), 'w') as f:
            f.writelines(self.web_lines)

    def run(self):
        self.io.use_analysis_cwd = False
        self.configure()
        if not self.image_postfix:
            return
        if self.image_names or self.subfolders or self.plain_info:
            self.message('INFO Building page in ' + self.working_dir)
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
            self.io.use_analysis_cwd = True

# TODO: Make breadcrumb links with '../'

