======
Varial
======


.. image:: https://travis-ci.org/HeinAtCERN/Varial.svg?branch=master
    :target: https://travis-ci.org/HeinAtCERN/Varial


Toolkit for analysis with ROOT. No gui, just library.

Documentation can be found at:
http://desy.de/~tholenhe/varial_doc/html/index.html

(By the way, this is a "Varial": https://www.youtube.com/watch?v=X0dxKbJ08d4)


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

In your shell, type ``varial_rootfileplotter.py`` (without arguments) to get a 
help message on how to specify inputs.


.. include:: docs/index.rst

