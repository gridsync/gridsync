#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import sys
import tempfile


_, p = tempfile.mkstemp()
shutil.make_archive(p, 'zip', sys.argv[1])
shutil.move(p + '.zip', sys.argv[2])
