===============
Getting started
===============

Prerequisites
-------------

The processing management starts to be reasonable, once more than one
analysis sample is concerned, when all samples are processed with (mostly) the
same cfg file.

For the efficient use of the post-processing tools, knowledge about python
generators and generator expressions is crucial. A nice overview with practical
application is given at http://www.dabeaz.com/generators/index.html .

Processing
==========

A minimal configuration of the processing unit is given below::

    import cmstoolsac3b.settings as settings
    settings.cfg_main_import_path = "CmsPackage.CmsModule.doMyAnalysis_cfg"

    import cmstoolsac3b_example.sampledefinition

    import cmstoolsac3b.main
    cmstoolsac3b.main.main(
        samples=cmstoolsac3b_example.sampledefinition
    )

When executed, this code takes the sample definitions, sets up the cmsRun cfg
files and runs them in the current working directory.

Settings
--------

The ``utilities.settings`` module defines project wide settings. These can be
accessed and changed from anywhere::

    import cmstoolsac3b.settings as settings
    settings.foo = "bar"
    print settings.mc_samples()

A default value is present for most settings.
In file ``cmstoolsac3b_examples/settingsprofile_proc.py`` the settings which are relevant to
cmsRun processing are demonstrated. Most members of the settings module are used
in post-processing. Have a look at ``cmstoolsac3b/settings.py``.

Sample definition
-----------------

An exhaustive example of the definition of samples is given in the file
``cmstoolsac3b_examples/sampledefinition.py`` (link: :ref:`sample-definition-example`) along
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
``cmstoolsac3b.postprocessing.PostProcTool`` for every tool you make.
See its doc for further details.
The postprocessing tools need to be passed into the main function::

    class MyTool(cmstoolsac3b.postprocessing.PostProcTool):
        def run(self):
            # do some tool stuff here

    cmstoolsac3b.main.main(
        post_proc_tool_classes=[MyTool]
    )

The example file ``cmstoolsac3b_examples/settingsprofile_postproc.py`` gives you an idea
about basic customization within the provided tools.

Take off
--------

Checkout ``cmstoolsac3b_examples/configexample.py`` and ``cmstoolsac3b_examples/postproctools.py`` to see
how the basic configuration works.
This page provides you with some general knowledge about
the ideas and concepts. It's always a good idea to look into the source code,
as I try to make things modular and understandable. Feedback is very welcome!
Again: Generators are important!
Checkout http://www.dabeaz.com/generators/index.html and the python
itertools package at http://docs.python.org/2/library/itertools.html .
