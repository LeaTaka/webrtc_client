#!/bin/sh

USER=pi
HOST=$1
date
scp -r * ${USER}@$HOST:webrtc_client/
ssh ${USER}@$HOST sudo systemctl restart lea
