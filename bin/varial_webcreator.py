#!/usr/bin/env python

import ROOT
ROOT.gROOT.SetBatch(True)

from varial.main import process_cmd_args
import varial.tools

process_cmd_args()
varial.tools.WebCreator('VarialWebCreator', no_tool_check=True).run()
