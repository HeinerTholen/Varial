#!/usr/bin/env python

import ROOT
ROOT.gROOT.SetBatch(True)

import varial.tools
varial.tools.WebCreator(no_tool_check=True).run()
