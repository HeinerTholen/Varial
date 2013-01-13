====================
The generator module
====================

Python generators help to process ROOT-objects, so you don't have to load and
manipulate wrappers one by one. Many generators are predefined here.
They generalize the operations and deliver utility functions.
The beauty of this approach becomes apparent when chaining generators.
Some chaining (or 'packaging') takes place at the bottom of this document,
starting with the ``fs_filter_sort_load`` generator.

Use the generators within the ``run()`` method of your Post-processing tools!
Also check out the Examples in :ref:`post-proc-example` to see the actual
application.

Module members
==============

.. automodule:: cmstoolsac3b.generators
   :members: