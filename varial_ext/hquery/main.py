import engine


def main(**kws):
    e = engine.HQueryEngine(kws)

    import server  # server should not be imported in backend process
    server.start(e)


# TODO SSL and security token/url
# TODO https://stackoverflow.com/questions/24110568/cherrypy-access-restrictions-with-static-files
