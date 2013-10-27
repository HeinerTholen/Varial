
import unittest
from test_diskio import suite as dip_suite
from test_generators import suite as gen_suite
from test_ops import suite as ops_suite
from test_rendering import suite as rnd_suite
#from test_postproctools import suite as pst_suite

import doctest
import cmstoolsac3b.generators as gen
import cmstoolsac3b.diskio as dsp
import cmstoolsac3b.history as hst
import cmstoolsac3b.operations as ops
import cmstoolsac3b.rendering as rnd
import cmstoolsac3b.wrappers as wrp

suite = unittest.TestSuite((
    doctest.DocTestSuite(wrp),
    doctest.DocTestSuite(hst),
    doctest.DocTestSuite(ops),
    doctest.DocTestSuite(dsp),
    doctest.DocTestSuite(rnd),
    doctest.DocTestSuite(gen),
    ops_suite,
    dip_suite,
    gen_suite,
    rnd_suite,
#    pst_suite,
))

import sys
if __name__ == '__main__':
    res = unittest.TextTestRunner(
        verbosity = 2
    ).run(suite)
    if res.failures:
        sys.exit(-1)

