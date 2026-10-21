#!/bin/sh
set -eu
umask 077
# bootstrap.py emits alphanumeric credentials. Reject unsafe JSON interpolation.
case "$S3_ACCESS_KEY$S3_SECRET_KEY" in *[!a-zA-Z0-9]*) echo 'Object-store keys must be alphanumeric'; exit 1;; esac
printf '{"identities":[{"name":"sceneguard","credentials":[{"accessKey":"%s","secretKey":"%s"}],"actions":["Admin","Read","List","Tagging","Write"]}]}' "$S3_ACCESS_KEY" "$S3_SECRET_KEY" > /tmp/s3.json
exec weed server -dir=/data -s3 -s3.port=9000 -s3.config=/tmp/s3.json -ip=objectstore -master.volumeSizeLimitMB=256 -volume.max=10
