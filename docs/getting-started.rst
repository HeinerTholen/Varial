.. _getting-started:

===============
Getting started
===============

Prerequisites
=============


For the efficient use of the histogram manipulation tools, knowledge about
python generators and generator expressions is kind of crucial. A nice guide
with practical application can be found at
http://www.dabeaz.com/generators/index.html
. Furthermore, the itertools package, at
http://docs.python.org/2/library/itertools.html
, is of great help.

- Root is needed: http://root.cern.ch
- CMSSW is optional


Installation
============

Installation is simple::

    git clone https://github.com/HeinAtCERN/Varial.git

Add this to your ``.bashrc`` or ``.bash_profile``::

    export PYTHONPATH=<your_path_to_varial>:PYTHONPATH


Version-logging
---------------

**DISCLAIMER: The API is under permanent construction.** In order to ensure you
can always get back to the Varial version you've build against, you should
copy the ``pre-commit`` script in the Varial base directory to ``.git/hooks``
in your own project. Make sure to add the correct path to Varial into the
``pre-commit`` script. For every commit that you now do, the script will put a
``VARIAL_VERSION`` file with the version hash of Varial into your project
directory and commit it as well. You can later rollback Varial by changing into
its directory and issuing::

    git checkout <version hash here>


TODO: Write the real 'getting started'
======================================

Loose list of points:
- introduce wrapping, operations and generators
- What does a tool/toolchain do?
- Automatic result handling
- auto rerunning of Tools
- make an analysis with and settings, samples

Some intro to tools::

    class MyTool(varial.postprocessing.PostProcTool):
        def run(self):
            # do some tool stuff here


Sample definition
-----------------

An exhaustive example of the definition of samples is given in the file
``varial_examples/sampledefinition.py`` (link:
:ref:`sampledefinition-example`) along with a number of comments and
explanations.


Take off
--------

Checkout ``varial_examples/configexample.py`` and ``varial_examples/postproctools.py`` to see
how the basic configuration works.
This page provides you with some general knowledge about
the ideas and concepts. It's always a good idea to look into the source code,
as I try to make things modular and understandable. Feedback is very welcome!
Again: Generators are important!
Checkout http://www.dabeaz.com/generators/index.html and the python
itertools package at  .

