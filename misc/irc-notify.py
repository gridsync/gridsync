#!/usr/bin/env python
"""
Quick and dirty IRC notification script.

Can be used with CI services like AppVeyor to enable basic event notifications.
Arguments passed to the script will be sent as message content and any
'{var}'-formatted environment variables will be expanded automatically. Use
commas to delineate multiple messages.

Example:
  python irc-notify.py '[{project_name}:{branch}] {short_commit}: "{message}" ({author}) {color_code}3Succeeded','Details: {build_url} | Commit: {commit_url}'
"""
import os, random, socket, ssl, sys, time

protected_vars = vars()
for key, value in dict(os.environ).items():
    if key not in protected_vars:
        vars()[key.lower()] = value
for key, value in dict(os.environ).items():
    if key.startswith('APPVEYOR_'):
        trimmed_key = key[9:].lower()
        split_key = key.split('_')[-1].lower()
        if trimmed_key not in vars():
            vars()[trimmed_key] = value
        if split_key not in vars():
            vars()[split_key] = value

short_commit = commit[0:7]
project_url = "{url}/project/{account_name}/{project_name}".format(**vars())
build_url = "{project_url}/build/{build_version}".format(**vars())
repo_url = "https://{repo_provider}.com/{repo_name}".format(**vars()).lower()
commit_url = "{repo_url}/commit/{repo_commit}".format(**vars())
username = (username if 'username' in vars() else 'appveyor')
color_code = "\x03"

messages = []
for message in ' '.join(sys.argv[1:]).split(','):
    messages.append(message.format(**vars()).strip())

s = ssl.wrap_socket(socket.socket(socket.AF_INET,socket.SOCK_STREAM))
s.connect((socket.gethostbyname("chat.freenode.net"), 6697))
s.send("NICK {0}\r\nUSER {0} * 0 :{0}\r\n".format(username).encode())
f = s.makefile()
while f:
    line = f.readline()
    print(line.rstrip())
    w = line.split()
    if w[0] == "PING":
        s.send("PONG {}\r\n".format(w[1]).encode())
    elif w[1] == "433":
        s.send("NICK {}{}\r\n".format(
            sys.argv[1], str(random.randint(1,9999))).encode())
    elif w[1] == "001":
        time.sleep(5)
        for message in messages:
            print("NOTICE #{} :{}".format(project_name, message))
            s.send("NOTICE #{} :{}\r\n".format(project_name, message).encode())
        time.sleep(5)
        sys.exit()
