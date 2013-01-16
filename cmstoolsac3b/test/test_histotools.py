
import unittest
from cmstoolsac3b.test.test_generators import suite as gen_suite
from cmstoolsac3b.test.test_histoDispatch import suite as dip_suite
from cmstoolsac3b.test.test_ops import suite as ops_suite
from cmstoolsac3b.test.test_rendering import suite as rnd_suite
from cmstoolsac3b.test.test_wrapper import suite as wrp_suite

import doctest
import cmstoolsac3b.generators as gen
import cmstoolsac3b.histodispatch as dsp
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
    gen_suite,
    dip_suite,
    ops_suite,
    rnd_suite,
    wrp_suite
))

if __name__ == '__main__':
    unittest.TextTestRunner().run(suite)

