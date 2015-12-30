from cherrypy.lib.static import serve_file
import cherrypy
import string
import socket
import random
import os
join = os.path.join


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
static_file_types = {
    '.png': 'image/png',
    '.json': 'application/json',
    '.rt': 'application/root',
}
session_token = ''.join(
    random.SystemRandom().choice(
        string.ascii_uppercase + string.digits) for _ in range(20))
session_token = session_token[:10] + 'hQuery' + session_token[10:]


def load_html(args):
    path = '/'.join(args)
    real_path = 'sections/' + path
    if os.path.isdir(real_path):
        real_path = join(real_path, 'index.html')
        path = join(path, 'index.html')

    if not (path.endswith('index.html') and os.path.isfile(real_path)):
        raise cherrypy.NotFound()

    with open(real_path) as f:
        return path, f.read()


class WebService(object):
    exposed = True

    def __init__(self, engine):
        self.engine = engine
        self.path = os.path.abspath(os.getcwd()) + '/sections'

    def GET(self, *args, **kws):
        if 'auth' not in cherrypy.session:
            print kws.get('s', '')
            print session_token
            if kws.get('s', '') == session_token:
                cherrypy.session['auth'] = True
            else:
                raise cherrypy.HTTPError(
                    '403 Forbidden',
                    'hQuery token unavaialbe or incorrect. Please restart the '
                    'server to get an URL with a fresh token.'
                )

        if not args:
            return redirect

        ext = os.path.splitext(args[-1])[1]
        if ext in static_file_types:
            return serve_file(join(self.path, *args),
                              content_type=static_file_types[ext])
        elif args == ('rootjs.html',):
            return serve_file(join(self.path, *args),
                              content_type='text/html')
        elif args[-1].endswith('index.html'):
            return self.engine.get(*load_html(args))
        else:
            raise cherrypy.NotFound()

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

        'tools.sessions.on': True,
        'tools.sessions.storage_type': 'file',
        'tools.sessions.storage_path': os.path.abspath(os.getcwd())
    },
    'global': {
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8080,
    }
}


def find_port(port):
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def test_port(num):
        try:
            soc.bind(('', num))
            return True
        except socket.error:
            return False

    while not test_port(port):
        port += 1
    soc.listen(1)
    soc.close()
    return port


def start(engine, ssl_conf=None):
    # find hostname and port
    hostname = socket.gethostname()
    port = find_port(8080)
    conf['global']['server.socket_port'] = port

    # apply ssl config
    if ssl_conf:
        conf['global'].update(ssl_conf)

    # print statement and go
    url = '{}://{}:{}/?s={}'.format(
        'https' if ssl_conf else 'http',
        '{}',
        port,
        session_token
    )
    print '='*80
    print 'hQuery is ready at:'
    print url.format(hostname)
    print url.format('127.0.0.1')
    print '='*80
    cherrypy.quickstart(WebService(engine), '/', conf)
