"""
Wrapper around pip to make it use reproducible temporary directory names
and to exclude debug information from compiled binaries.
"""
import os
import sys
import tempfile

import pip


# Normalize timestamps for compiled C extensions via undocumented MSVC flag.
# See https://nikhilism.com/post/2020/windows-deterministic-builds/ and/or
# https://blog.conan.io/2019/09/02/Deterministic-builds-with-C-C++.html
if sys.platform == "win32"
    os.environ["LINK"] = "/Brepro"
else:
    # Disable debug information.
    os.environ["CFLAGS"] = "-g0"

tempfile._get_candidate_names().rng.seed(0)
pip.main()
