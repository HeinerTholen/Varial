"""
Tools connected to the use of (La)Tex.
"""

import shutil
import os

from varial.toolinterface import Tool


class TexContent(Tool):
    """
    Copies (and converts) content for usage in a tex document.

    For blocks of images, includestatements are printed into .tex files.
    These can be include in the main tex document.

    Image files in eps format are converted to pdf.

    IMPORTANT: absolute paths must be used in ``images`` and ``plain_files``!

    :param images:      ``{'blockname.tex': ['path/to/file1.eps', ...]}``
    :param plain_files: ``{'target_filename.tex': 'path/to/file1.tex', ...}``
    :param include_str: e.g. ``r'\includegraphics[width=0.49\textwidth]
                        {TexContent/%s}'`` where %s will be formatted with the
                        basename of the image
    :param dest_dir:    destination directory (default: tool path)
    """
    def __init__(self,
                 images,
                 plain_files,
                 include_str,
                 dest_dir=None,
                 name=None):
        super(TexContent, self).__init__(name)
        self.images = images
        self.tex_files = plain_files
        self.include_str = include_str
        self.dest_dir = dest_dir

    def _join(self, basename):
        return os.path.join(self.dest_dir, basename)

    @staticmethod
    def _hashified_filename(path):
        bname, ext = os.path.splitext(os.path.basename(path))
        hash_str = '_' + hex(hash(path))[-7:]
        return bname + hash_str

    def copy_image_files(self):
        for blockname, blockfiles in self.images.iteritems():
            hashified_and_path = list(
                (self._hashified_filename(bf), bf) for bf in blockfiles
            )

            # copy image files
            for hashified, path in hashified_and_path:
                p, ext = os.path.splitext(path)
                if ext == '.eps':
                    os.system('ps2pdf -dEPSCrop %s.eps %s.pdf' % (p, p))
                    ext = '.pdf'
                elif not ext in ('.pdf', '.png'):
                    raise RuntimeError(
                        'Only .eps, .pdf and .png images are supported.')
                shutil.copy(p+ext, self._join(hashified+ext))

            # make block file
            with open(self._join(blockname), 'w') as f:
                for hashified, _ in hashified_and_path:
                    f.write(self.include_str % hashified + '\n')

    def copy_plain_files(self):
        for fname, path, in self.tex_files.iteritems():
            shutil.copy(path, self._join(fname))

    def run(self):
        if not self.dest_dir:
            self.dest_dir = self.cwd
        self.copy_image_files()
        self.copy_plain_files()
