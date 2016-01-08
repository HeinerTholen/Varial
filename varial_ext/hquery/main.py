import engine


def main(**kws):
    e = engine.HQueryEngine(kws)

    import server  # server should not be imported in backend process
    server.start(e)


# TODO communicate with job submitter (warn when only few jobs are running)
# TODO check if 0 events are selected (problems with log) and raise error
# TODO think about pulling everything through GET
# TODO first make histos for current section, send reload, then others
# TODO lines in plots if selection is applied (imporved N-1 feature)
# TODO SGEJobSubmitter: Jobs are killed after 1 hour. Resubmit before that.
# TODO cut efficiency
# TODO histo_form: put width into CSS block
# TODO separate CSS file for all hquery-related fields
