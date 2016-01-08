import engine


def main(**kws):
    e = engine.HQueryEngine(kws)

    import server  # server should not be imported in backend process
    server.start(e)


# TODO link all selection forms
# TODO status from job submitter (warn when only few jobs are running)
# TODO progress bar or (n_done / n_all) statement
# TODO think about pulling everything through GET
# TODO first make histos for current section, send reload, then others
# TODO lines in plots if selection is applied (improved N-1 feature)
# TODO SGEJobSubmitter: Jobs are killed after 1 hour. Resubmit before that.
# TODO cut efficiency / cutflow plot in map reduce
# TODO histo_form: put width into CSS block
# TODO separate CSS file for all hquery-related fields
