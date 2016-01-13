import engine


def main(**kws):
    e = engine.HQueryEngine(kws)

    import server  # server should not be imported in backend process
    server.start(e)


# TODO multiple instances: add random token to jug_file path (clearing dirs??)
# TODO link all selection forms:
# TODO     https://stackoverflow.com/questions/12370653/split-html-forms
# TODO CUTFLOW
# TODO hint toggles (on bins vs. low, high / CUTFLOW)
# TODO add multiple histos (toggled form)
# TODO add multiple histos e.g. store histos via python, not in json
# TODO reloading: use ajax instead of full reload
# TODO status from job submitter (warn when only few jobs are running)
# TODO progress bar or (n_done / n_all) statement
# TODO progress: sometimes it hangs until done. Why?
# TODO first make histos for current section, send reload, then others
# TODO lines in plots if selection is applied (improved N-1 feature)
# TODO SGEJobSubmitter: Jobs are killed after 1 hour. Resubmit before that.
# TODO cut efficiency / cutflow plot in map reduce
# TODO histo_form: put width into CSS block
# TODO separate CSS file for all hquery-related fields
# TODO think about pulling everything through GET
