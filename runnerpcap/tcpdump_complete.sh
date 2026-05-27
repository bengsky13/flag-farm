#!/bin/bash
PKAPPA2_IP=127.0.0.1
PKAPPA2_PORT=8080
echo "FINISHED $1"

curl --data-binary "@$1" http://${PKAPPA2_IP}:${PKAPPA2_PORT}/upload/`basename $1`

rm "$1"