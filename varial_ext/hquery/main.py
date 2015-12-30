import engine


def main(**kws):
    ssl_conf = kws.pop('ssl_conf', '')
    e = engine.HQueryEngine(kws)

    import server  # server should not be imported in backend process
    server.start(e, ssl_conf)


# TODO test SSL
# TODO check if 0 events are selected (problems with log) and raise error
# TODO think about pulling everything through GET
