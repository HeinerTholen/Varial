import subprocess
import time
import os


class SGEWorker(object):
    def __init__(self, task_id, jug_file_path, jug_file_path_pat):
        self.task_id = task_id
        self.jug_file_path = jug_file_path
        self.jug_file_path_pat = jug_file_path_pat

    def start(self):
        print 'SGEWorker started! task_id:', self.task_id

        proc = None
        while True:
            if proc:
                # wait here until proc is finished
                while None == proc.returncode:
                    time.sleep(0.5)
                    proc.poll()

                # raise on returncode else we're done.
                if proc.returncode:
                    raise RuntimeError(
                        'jug execute returncode != 0: %d' % proc.returncode)

                proc = None

            elif os.path.exists(self.jug_file_path):
                proc = subprocess.Popen(
                    'jug execute %s' % self.jug_file_path, shell=True)

            # nothing to do...
            time.sleep(0.5)


# TODO be social. work for others, when there's no work for you.

