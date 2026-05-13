#! /usr/bin/env sh
set -e
docker run -v "$(pwd)":/repo italia/publiccode-parser-go /repo/publiccode.yml
