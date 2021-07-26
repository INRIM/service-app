#!/bin/bash
source .env
if [ -z "${STACK}" ]; then
   export STACK="service-app"
fi
docker logs --follow ${STACK}_backend