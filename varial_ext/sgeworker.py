import random
import glob
import time
import jug
import os


class SGEWorker(object):
    def __init__(self, task_id, username, jug_file_path_pat):
        self.task_id = task_id
        self.username = username
        self.jug_file_path_pat = jug_file_path_pat

    def do_work(self, work_path):
        try:
            print 'INFO trying to start jugfile:', work_path
            if os.path.exists(work_path):
                jug.jug.main(['', 'execute', work_path])

        # happens when the jugfile is removed before reading
        except IOError:
            pass

        # real errors from map/reduce
        except RuntimeError as e:
            try:
                os.remove(work_path)

            except OSError:
                return  # if jugfile is already removed, someone else prints e

            err_path = work_path.replace('.py', '.err.txt')
            with open(err_path, 'w') as f:
                f.write(repr(e))

        # (Errors other then IOError and RuntimeError let the worker crash.)

    def find_work_forever(self):
        search_path = self.jug_file_path_pat.format(user='*')
        user = '/%s/' % self.username

        while True:
            # look for work (all users)
            work_paths = glob.glob(search_path)

            # look for own stuff first  (_or_'d with all work)
            work_paths = filter(lambda p: user in p, work_paths) or work_paths

            if work_paths:
                work = random.choice(work_paths)
                self.do_work(work)
            else:
                time.sleep(1.)

    def start(self):
        print 'SGEWorker started!'
        print 'SGEWorker task_id:           ', self.task_id
        print 'SGEWorker username:          ', self.username
        print 'SGEWorker jug_file_path_pat: ', self.jug_file_path_pat

        self.find_work_forever()


# python -c "from varial.extensions.sgeworker import SGEWorker; SGEWorker(3, 'tholenhe', '/nfs/dust/cms/user/{user}/varial_sge_exec/jug_file.py').start(); "
