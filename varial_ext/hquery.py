import os
import cherrypy
from hquery_engine import engine


def load_html(args):
    path = '/'.join(args)
    if os.path.isdir(path):
        path = os.path.join(path, 'index.html')

    if not (path.endswith('index.html') and os.path.isfile(path)):
        raise cherrypy.NotFound()

    with open(path) as f:
        return path, f.read()


class WebService(object):
    exposed = True

    def GET(self, *args, **kws):
        return engine.get(*load_html(args))

    def POST(self, *args, **kws):
        engine.post(args, kws)
        return engine.get(*load_html(args))

    def PUT(self, *args, **kws):
        pass  # using only html forms

    def DELETE(self, *args, **kws):
        pass  # using only html forms


conf = {
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'tools.response_headers.on': True,
        'tools.response_headers.headers': [('Content-Type', 'text/html')],

        'tools.staticdir.on': True,
        'tools.staticdir.root': os.path.abspath(os.getcwd()),
        'tools.staticdir.match': r'(\.png$)',  # TODO: *.rt rootjs.html
        'tools.staticdir.dir': '.',
    }
}


def start():
    return cherrypy.quickstart(WebService(), '/', conf)
