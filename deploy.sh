#!/bin/sh

USER=pi
HOST=$1
date
scp -r * ${USER}@$HOST:webrtcClient/
ssh ${USER}@$HOST sudo systemctl restart lea
