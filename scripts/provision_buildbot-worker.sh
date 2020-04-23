#!/bin/sh
python2 -m pip install buildbot-worker
buildbot-worker create-worker ~/buildbot "$BUILDBOT_HOST" "$BUILDBOT_NAME" "$BUILDBOT_PASS"
buildbot-worker restart ~/buildbot
