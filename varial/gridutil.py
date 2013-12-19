
import os
import subprocess


def gen_filter_htholen(src):
    """My datasets and files have 'htholen' as a token inside."""
    for line in src:
        if "htholen" in line:
            yield line


def gen_srmls_lines_to_file_lines(srmls_lines):
    for line in srmls_lines:
        yield line.split()[-1]


def srmls_lines(dcache_path):
    proc = subprocess.Popen(["srmls", dcache_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    res = proc.communicate()
    if proc.returncode:
        raise RuntimeError("srmls failed:" + str(res))
    return res


def dbs_query(query_str):
    cmd = [
        "dbs " +
        "search " +
        '--url="https://cmsdbsprod.cern.ch:8443/cms_dbs_ph_analysis_02_writer/servlet/DBSServlet" ' +
        '--query "'+query_str+'"'
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    res = proc.communicate()
    if proc.returncode:
        raise RuntimeError("dbs failed:" + str(res))
    return list(res[0].split())


def dbs_query_for_files(datasetname):
    return dbs_query("find file where dataset = "+datasetname)


def dbs_query_for_dataset(query_str):
    return dbs_query("find dataset where dataset = "+query_str)


def copy_file_from_dcache(dcache_path, dest_dir=None):
    proc = subprocess.Popen([
            "uberftp " +
            "grid-ftp.physik.rwth-aachen.de " +
            '"get '+dcache_path+'"',
        ],
        cwd=dest_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    res = proc.communicate()
    if proc.returncode:
        raise RuntimeError("uberftp failed:" + str(res))


def copy_all_datasets(query_str, sample_name_func):
    all_datasets = list(gen_filter_htholen(dbs_query_for_dataset(query_str)))
    for d in all_datasets:
        print "working on dataset: ", d
        files = gen_filter_htholen(dbs_query_for_files(d))
        sample = sample_name_func(d)
        if not os.path.exists(sample):
            os.mkdir(sample)
        else:
            continue
        for file in files:
            copy_file_from_dcache("/pnfs/physik.rwth-aachen.de/cms"+file, sample)



