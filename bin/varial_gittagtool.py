#!/usr/bin/env python

import ROOT
ROOT.gROOT.SetBatch(True)

import varial.extenstions.git as git
import sys

if len(sys.argv) < 2:
    print "Usage:"
    print "varial_gittagtool.py <logfile_path> [<commit_msg_prefix>]"
    print ""
    exit(-1)

git.GitAdder().run()
if len (sys.argv) == 2:
	git.GitTagger(sys.argv[1]).run()
if len (sys.argv) > 2:
	git.GitTagger(sys.argv[1], sys.argv[2]).run()
