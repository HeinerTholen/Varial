import engine


def main(**kws):
    e = engine.HQueryEngine(kws)

    import server  # server should not be imported in backend process
    server.start(e)


# TODO test SSL
# TODO check if 0 events are selected (problems with log) and raise error
# TODO think about pulling everything through GET
