#!/usr/bin/env python

"""
You can copy this script to change settings.

Add colors like this:

import varial
varial.settings.colors.update({
    'TTbar': 643,
    'WJets': 522,
})

For more stuff to be adjusted, check the varial.settings module. Everything
in there can be adjusted before the last two lines of this script here.
"""

import varial_example.varial_plotter as rfp
rfp.run()
