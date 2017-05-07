#!/usr/bin/env python

"""
Base script to call the varial plotter. Copy and adjust to your need.



Changing settings
=================

For stuff to be adjusted, check the ``varial.settings`` module. Everything
in there can be adjusted before the last two lines of this script here.


Adding colors
-------------

import varial
varial.settings.colors.update({
    'TTbar': 643,
    'WJets': 522,
})



Control over content!
=====================

It is possible to define functions that are called on every histogram during
plotting. These functions can be defined here and must be passed to the
plotter via ``rfp.run(args...)`` at the end of the script. For a list of
arguments, check the ``varial.plotter.mk_rootfile_plotter`` function and
the ``varial.plotter.Plotter`` class.


Plotting selected histograms
----------------------------

In order to filter histograms, a key-function can be implemented::

    def signal_region_key_function(histo_wrapper):
        return 'SignalRegion' in histo_wrapper.in_file_path

This function returns true, if the variable 'in_file_path' contains
'SignalRegion'. The function must be handed over to the plotter::

    rfp.run(filter_keyfunc=signal_region_key_function)


Wait. Variables??
-----------------

In Varial, histograms are handled in containers, so-called wrappers. See the
``varial.wrappers`` module for details. They are pipelined with python
generators. Here's a generator that prints all histograms that fly by::

    def print_all_wrappers(histo_wrappers):
        for h in histo_wrappers:
            print h
            yield h

This will print the wrapper with all variables and the information they
contain. Add it like so::

    rfp.run(hook_loaded_histos=print_all_wrappers)


Manipulating histograms
-----------------------

The ``hook_loaded_histos`` argument accepts generators (or functions that take
a list of wrappers and return a list of wrappers). The function is called
immediately after the histograms are loaded from file.

As an examples, this one here scales up your signal histograms by a factor of
twenty::

    def magnify_signal(histo_wrappers):
        for h in histo_wrappers:
            if h.is_signal:
                h.histo.Scale(20.)
            yield h



Control over canvas
===================

The list ``varial.rendering.post_build_funcs`` contain functions that are
called after the main canvas is build. By default it contains a function to
make ratio plots and a function to make the legend. Check the
``varial.rendering`` module for details. Here's how to add a simple box atop
the canvas. The ``mk_tobject_draw_func`` function will take any TObject::

    import varial
    lumibox = varial.ROOT.TPaveText(0.5, 0.823, 0.7, 0.923, 'brNDC')
    lumibox.AddText('One bazzillion fb^{-1} (21.1 Giggawatts)')
    lumibox.SetTextSize(0.042)
    lumibox.SetFillStyle(0)
    lumibox.SetBorderSize(0)
    lumibox.SetTextAlign(31)
    lumibox.SetMargin(0.0)
    lumibox.SetFillColor(0)

    varial.rendering.post_build_funcs.append(
        varial.rendering.mk_tobject_draw_func(lumibox)
    )
"""


import varial_example.varial_plotter as rfp
rfp.run()
