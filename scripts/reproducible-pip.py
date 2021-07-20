"""
Wrapper around pip to make it use reproducible temporary directory names.
"""
import os
import tempfile

import pip

# Disable debug information.
os.environ["CFLAGS"] = "-g0"

tempfile._get_candidate_names().rng.seed(0)
pip.main()
