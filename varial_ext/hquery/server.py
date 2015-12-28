import os
import cherrypy


redirect = """\
<!DOCTYPE HTML>
<html lang="en-US">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="1;url=index.html">
        <script type="text/javascript">
            window.location.href = "index.html"
        </script>
        <title>Page Redirection</title>
    </head>
    <body>
        If you are not redirected automatically,
        follow this <a href='index.html'>link to index.html</a>
    </body>
</html>
"""


def load_html(args):
    path = '/'.join(args)
    real_path = 'sections/' + path
    if os.path.isdir(real_path):
        real_path = os.path.join(real_path, 'index.html')
        path = os.path.join(path, 'index.html')

    if not (path.endswith('index.html') and os.path.isfile(real_path)):
        raise cherrypy.NotFound()

    with open(real_path) as f:
        return path, f.read()


class WebService(object):
    exposed = True

    def __init__(self, engine):
        self.engine = engine

    def GET(self, *args, **kws):
        if not args:
            return redirect
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
        'tools.staticdir.index': 'index.html',
        'tools.staticdir.root': os.path.abspath(os.getcwd()) + '/sections',
        'tools.staticdir.match': r'(\S+\.png|\S+\.rt|rootjs\.html)$',
        'tools.staticdir.dir': '.',
    },
    'global': {
        'server.socket_host': '127.0.0.1',  # '0.0.0.0',
    }
}


def start(engine):
    cherrypy.quickstart(WebService(engine), '/', conf)
