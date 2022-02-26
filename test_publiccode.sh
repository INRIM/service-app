#! /usr/bin/env sh
set -e
docker run -i italia/publiccode-parser-go -remote-base-url https://raw.githubusercontent.com/INRIM/service-app/master /dev/stdin < publiccode.yml
