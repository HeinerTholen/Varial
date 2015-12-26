import engine


def main(**kws):
    e = engine.HQueryEngine(kws)

    import server  # server should not be imported in backend process
    server.start(e)
