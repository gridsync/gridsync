"""
Wrapper around pip to make it use reproducible temporary directory names.
"""
import tempfile

import pip

tempfile._get_candidate_names().rng.seed(0)
pip.main()
