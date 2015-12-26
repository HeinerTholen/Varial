import os
import cherrypy


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

    def __init__(self, engine):
        self.engine = engine

    def GET(self, *args, **kws):
        return self.engine.get(*load_html(args))

    def POST(self, *args, **kws):
        self.engine.post(args, kws)
        return self.engine.get(*load_html(args))

    def PUT(self, *args, **kws):
        pass  # using html forms only

    def DELETE(self, *args, **kws):
        pass  # using html forms only


conf = {
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'tools.response_headers.on': True,
        'tools.response_headers.headers': [('Content-Type', 'text/html')],

        'tools.staticdir.on': True,
        'tools.staticdir.root': os.path.abspath(os.getcwd()),
        'tools.staticdir.match': r'(\S+\.png|\S+\.rt|rootjs\.html)$',
        'tools.staticdir.dir': '.',
    }
}


def start(engine):
    cherrypy.quickstart(WebService(engine), '/', conf)
