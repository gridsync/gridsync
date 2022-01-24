"""
Ported to Python 3.
"""

from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from future.utils import PY2
if PY2:
    from future.builtins import filter, map, zip, ascii, chr, hex, input, next, oct, open, pow, round, super, bytes, dict, list, object, range, str, max, min  # noqa: F401


import sys

print("#####################################################################")
import certifi, os, pprint
print("certifi.where() = ", certifi.where())
pprint.pprint(dict(os.environ))
print("#####################################################################")


from twisted.internet.task import react
from twisted.internet.defer import inlineCallbacks
import treq

@inlineCallbacks
def main(reactor):
    resp = yield treq.get("https://github.com")
    print(resp.code)


from allmydata.scripts.runner import run

if __name__ == "__main__":
    #sys.exit(run())
    react(main)
