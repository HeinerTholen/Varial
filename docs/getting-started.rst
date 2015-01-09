.. _getting-started:

===============
Getting started
===============

Prerequisites
=============


For the efficient use of the histogram manipulation tools, knowledge about
python generators and generator expressions is kind of crucial. A nice guide
with practical application can be found at
http://www.dabeaz.com/generators/index.html .

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


Processing
==========

A minimal configuration of the processing unit is given below::

    import varial.settings as settings
    settings.cfg_main_import_path = "CmsPackage.CmsModule.doMyAnalysis_cfg"

    import varial_example.sampledefinition

    import varial.main
    varial.main.main(
        samples=varial_example.sampledefinition
    )

When executed, this code takes the sample definitions, sets up the cmsRun cfg
files and runs them in the current working directory.

Settings
--------

The ``varial.settings`` module defines project wide settings. These can be
accessed and changed from anywhere::

    import varial.settings as settings
    settings.foo = "bar"
    print settings.mc_samples()

A default value is present for most settings.
In file ``varial_examples/settingsprofile_proc.py`` the settings which are relevant to
cmsRun processing are demonstrated. Most members of the settings module are used
in post-processing. Have a look at ``varial/settings.py``.

Sample definition
-----------------

An exhaustive example of the definition of samples is given in the file
``varial_examples/sampledefinition.py`` (link: :ref:`sampledefinition-example`) along
with a number of comments and explanations.

Post-Processing
===============

Post-processing employs wrappers for histograms, stacks, canvases and the like
(simply called 'ROOT-objects' for now). They are created when a ROOT-object is
created or loaded from disk and they carry useful information about the
ROOT-object. You can directly apply operations to one or more wrappers, which
in turn operate on the ROOT-objects and the carried information. Python
generators are used to roll out these operations on multiple ROOT-objects all
at once. If you want to use ROOT-objects across many tools, they can be stored
in a pool.

In order to use post-processing, you need to subclass
``varial.postprocessing.PostProcTool`` for every tool you make.
See its doc for further details.
The postprocessing tools need to be passed into the main function::

    class MyTool(varial.postprocessing.PostProcTool):
        def run(self):
            # do some tool stuff here

    varial.main.main(
        post_proc_tool_classes=[MyTool]
    )

The example file ``varial_examples/settingsprofile_postproc.py`` gives you an idea
about basic customization within the provided tools.

Take off
--------

Checkout ``varial_examples/configexample.py`` and ``varial_examples/postproctools.py`` to see
how the basic configuration works.
This page provides you with some general knowledge about
the ideas and concepts. It's always a good idea to look into the source code,
as I try to make things modular and understandable. Feedback is very welcome!
Again: Generators are important!
Checkout http://www.dabeaz.com/generators/index.html and the python
itertools package at http://docs.python.org/2/library/itertools.html .

