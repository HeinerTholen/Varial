import subprocess
import random
import glob
import time
import jug
import os


################################################################# Submitter ###
# python -c "from varial_ext.sgeworker import SGESubmitter; SGESubmitter(10, '/nfs/dust/cms/user/{user}/varial_sge_exec', '/nfs/dust/cms/user/{user}/varial_sge_exec/jug_file_*.py').start(); "

sge_job_conf = """#!/bin/bash
#$ -l os=sld6
#$ -l site=hh
#$ -cwd
#$ -V
#$ -l h_rt=01:00:00
#$ -l h_vmem=2G
#$ -l h_fsize=2G#
#$ -o {jug_log_dir}/
#$ -e {jug_log_dir}/
#$ -t 1-{num_sge_jobs}
cd /tmp/
python -c "\
from varial.extensions.sgeworker import SGEWorker; \
SGEWorker(${SGE_TASK_ID}, '{user}', '{jug_file_path_pat}').start(); \
"
"""


class SGESubmitter(object):
    def __init__(self, n_jobs_max, jug_work_dir_pat, jug_file_search_pat):
        self.n_jobs_max = n_jobs_max
        self.jug_file_search_pat = jug_file_search_pat
        self.username = os.getlogin()

        self.jug_work_dir = jug_work_dir_pat.format(user=self.username)
        self.jug_log_dir = self.jug_work_dir.replace(
            'varial_sge_exec', 'varial_sge_log')

        # prepare dirs
        if not os.path.exists(self.jug_log_dir):
            os.mkdir(self.jug_log_dir)

        if not os.path.exists(self.jug_work_dir):
            os.mkdir(self.jug_work_dir)
            os.system('chmod g+w %s' % self.jug_work_dir)
            os.system('umask g+w %s' % self.jug_work_dir)  # let's collaborate!

        # clear some dirs
        exec_pat = jug_file_search_pat.format(
            user=self.username).replace('.py', '')
        log_pat = self.jug_log_dir + '/jug_worker.sh.*'
        if glob.glob(exec_pat):
            os.system('rm -rf ' + exec_pat)
        if glob.glob(log_pat):
            os.system('rm -rf ' + log_pat)

    @staticmethod
    def parse_num_jobs(qstat_line):
        if not qstat_line.strip():  # empty line
            return 0
        token = qstat_line.split()[-1]  # get last column
        if ':' in token:  #
            running, tot = token.split(':')[0].split('-')
            return int(tot) - int(running)
        else:
            return 1

    def submit(self):
        # how many are needed?
        qstat_cmd = ['qstat | grep jug_worker']
        proc = subprocess.Popen(qstat_cmd, shell=True, stdout=subprocess.PIPE)
        res = proc.communicate()[0]
        res = (self.parse_num_jobs(line) for line in res.split('\n'))
        n_workers = sum(res)
        n_workers_needed = self.n_jobs_max - n_workers

        # only submit if at least 5 workers are needed
        if n_workers_needed < 5:
            return

        # prepare sge config with paths
        job_sh = os.path.join(self.jug_work_dir, 'jug_worker.sh')
        with open(job_sh, 'w') as f:
            f.write(sge_job_conf.format(
                SGE_TASK_ID='{SGE_TASK_ID}',  # should stay
                jug_log_dir=self.jug_log_dir,
                num_sge_jobs=n_workers_needed,
                user=self.username,
                jug_file_path_pat=self.jug_file_search_pat,
            ))

        qsub_cmd = ['qsub ' + job_sh]
        proc = subprocess.Popen(qsub_cmd, shell=True, stdout=subprocess.PIPE)
        res = proc.communicate()[0]
        if not res.strip():
            raise RuntimeError('Job submission failed.')

    def start(self, every_x_mins=5):
        while True:
            self.submit()
            time.sleep(60*every_x_mins)


#################################################################### Worker ###
# python -c "from varial_ext.sgeworker import SGEWorker; SGEWorker(3, 'tholenhe', '/nfs/dust/cms/user/{user}/varial_sge_exec/jug_file.py').start(); "

class SGEWorker(object):
    def __init__(self, task_id, username, jug_file_path_pat):
        self.task_id = task_id
        self.username = username
        self.jug_file_path_pat = jug_file_path_pat

    @staticmethod
    def do_work(work_path):
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
