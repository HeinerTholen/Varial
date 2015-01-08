=============
Wrapper types
=============

The image below shows the class diagram of the wrapper types, along with their
fields. They are defined in ``histotools/wrappers.py`` . A HistoWrapper holds a
'histo', a FloatWrapper holds 'float' variable and so on.. The StackWrapper has
a histo variable as well, which hold the sum of its component histograms.

.. image:: wrappers.png

The aliases on the left describe histograms, which are not loaded yet. They are
created in the first place. After filtering and sorting these, the actual
histogram is loaded for every alias. Don't worry about ``_dict_base`` for now,
as it only provides some common methods.

Module members
==============

.. automodule:: varial.wrappers
   :members:
   :show-inheritance:

