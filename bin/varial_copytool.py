#!/usr/bin/env python

import varial.tools
import sys

if len(sys.argv) < 3:
    print "Usage:"
    print "varial_copytool.py <src_dir> <destination_dir>"
    print ""

varial.tools.CopyTool(sys.argv[2], sys.argv[1]).run()
