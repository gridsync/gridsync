#!/usr/bin/env python
"""
Quick and dirty IRC notification script.

Any '{var}'-formatted environment variables names will be expanded
along with git "pretty" format placeholders (like "%H" for commit hash,
"%s" for commit message subject, and so on). Use commas to delineate
multiple messages.

Example:
  python scripts/irc-notify.py chat.freenode.net:6697/#gridsync \[{branch}:%h\] {color}3$(python scripts/sha256sum.py dist/Gridsync.AppImage),:\)
"""
import os, random, socket, ssl, subprocess, sys, time
from subprocess import check_output as _co

color = "\x03"
branch = _co(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()

def _pf(s):
    if "%" not in s:
        return s
    return _co(["git", "log", "-1", "--pretty={}".format(s)]).decode().strip()

protected_vars = vars().keys()
for key, value in os.environ.items():
    if key.lower() not in protected_vars:
        vars()[key.lower()] = value

messages = []
for msg in " ".join(sys.argv[2:]).split(","):
    messages.append(_pf(msg.format(**vars())).strip())

_addr = sys.argv[1].split("/")[0]
_dest = sys.argv[1].split("/")[1]
_host = _addr.split(":")[0]
_port = _addr.split(":")[1]
_user = socket.gethostname().replace(".", "_")

try:
    s = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    s.connect((socket.gethostbyname(_host), int(_port)))
    s.send("NICK {0}\r\nUSER {0} * 0 :{0}\r\n".format(_user).encode())
    f = s.makefile()
    while f:
        line = f.readline()
        print(line.rstrip())
        w = line.split()
        if w[0] == "PING":
            s.send("PONG {}\r\n".format(w[1]).encode())
        elif w[1] == "433":
            s.send(
                "NICK {}-{}\r\n".format(
                    _user, str(random.randint(1, 9999))
                ).encode()
            )
        elif w[1] == "001":
            time.sleep(5)
            for msg in messages:
                print("NOTICE {} :{}".format(_dest, msg))
                s.send("NOTICE {} :{}\r\n".format(_dest, msg).encode())
            time.sleep(5)
            sys.exit()
except Exception as exc:
    print("Error: {}".format(str(exc)))
    sys.exit()
