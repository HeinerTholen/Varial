.. image:: https://travis-ci.org/HeinerTholen/Varial.svg?branch=master
    :target: https://travis-ci.org/HeinerTholen/Varial


======
Varial
======


One-click analysis with ROOT.

Documentation can be found at:
http://desy.de/~tholenhe/varial_doc/html/index.html


Installation
============

Varial is installed by cloning the git repository. In order to make it work in
your environment, you need to add the Varial base directory to the
``PYTHONPATH`` environment variable and the bin directory to your ``PATH``
variable::

   export PYTHONPATH=$PYTHONPATH:<path-to-Varial>
   export PATH=$PATH:<path-to-Varial>/bin


Basic plotting
==============

In your shell, type ``varial_plotter.py`` (without arguments) to get a
help message on how to specify inputs.


.. include:: docs/index.rst


hQuery
======

Interactive event selection and plotting, driven with Apache Spark.

.. image:: https://raw.githubusercontent.com/HeinerTholen/Varial/master/docs/sc_hQuery.png
