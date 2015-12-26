"""hQuery"""

from multiprocessing import Process, Queue
import html


def _start_backend(kws, q_in, q_out):
    from backend import HQueryBackend
    HQueryBackend(kws, q_in, q_out).start()


class HQueryEngine(object):
    def __init__(self, kws):
        self.messages = []

        self.backend_q_in = Queue()
        self.backend_q_out = Queue()
        self.backend_proc = Process(
            target=_start_backend,
            args=(kws, self.backend_q_in, self.backend_q_out)
        )
        self.backend_proc.start()
        if self.backend_q_out.get() != 'backend ready':
            raise RuntimeError('backend could not be started')

    def write_messages(self, cont):
        placeholder = '<!-- MESSAGE -->'
        if self.messages:
            self.messages.append(
                '<a href="index.html">reload</a>'
            )
        message = '\n'.join('<pre>%s</pre>' % m
                             for m in self.messages)
        message = '<div class="msg">\n' + message + '\n</div>'
        self.messages = []
        return cont.replace(placeholder, message)

    def post(self, args, kws):
        self.messages.append('POST %s %s' % (args, kws))
        self.backend_q_in.put((args, kws))

    def get(self, path, cont):
        cont = self.write_messages(cont)
        depth = path.count('/')
        if not depth:
            cont = html.add_section_create_form(cont)
        elif depth == 1:
            cont = html.add_section_manipulate_forms(cont, path)
            cont = html.add_histo_create_form(cont)
            cont = html.add_histo_manipulate_forms(cont)
        return cont

    def __del__(self):
        self.backend_q_in.put('terminate')
        self.backend_proc.join()
