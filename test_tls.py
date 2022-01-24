import os
import pprint
import sys

import certifi
import treq
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import react

os.environ["SSL_CERT_FILE"] = certifi.where()

print("#####################################################################")
pprint.pprint(dict(os.environ))
print("#####################################################################")


@inlineCallbacks
def main(reactor):
    resp = yield treq.get("https://github.com")
    print(resp.code)
    if resp.code != 200:
        sys.exit(1)


if __name__ == "__main__":
    print("certifi.where() = ", certifi.where())
    react(main)
