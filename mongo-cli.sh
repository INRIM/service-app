#!/bin/bash
source .env
if [ -z "${STACK}" ]; then
   export STACK="service-app"
fi
docker exec -ti mongo-${STACK} /bin/bash;