.. CmsAnalysisAC3B documentation master file, created by
   sphinx-quickstart on Tue Nov 20 14:11:41 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.



Welcome to CmsToolsAC3b's documentation!
===========================================

This package provides aiding tools for performing an analysis with the CMSSW
framework.
The application is divided into the steps 'processing' and 'post-processing'.
A typical use case would be to declare a set of ``Sample`` definitions, which
are transformed into cfg files for cmsRun. A main cfg file is imported. The
cmsRun-processes can be executed automatically (processing).
Possible post-processing steps would be to load histograms from the cmsRun
FileService output and plot them in a meaningful manner. The user is provided
with a set of tools to load, manipulate, combine and print histograms. Its
syntax is focused on streaming of objects.

Contents:

.. toctree::
   :maxdepth: 2

   intro.rst
   examples.rst
   reference.rst


Jump to module:

.. toctree::
   :maxdepth: 1

   generators.rst
   wrappers.rst
   rendering.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

