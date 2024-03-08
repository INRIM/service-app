#!/bin/bash
echo "clean project"
source ${PWD}/.env

if [ -z "${MONGO_PORT}" ]; then
   export MONGO_PORT=27018
fi
if [ -z "${SERVER_PORT}" ]; then
   export SERVER_PORT=8225
fi
if [ -z "${CLIENT_PORT}" ]; then
   export CLIENT_PORT=8526
fi
if [ -z "${STACK}" ]; then
   export STACK="service-app"
fi

docker compose -f docker-compose.yml -p ${STACK} --profile all down --rmi all --remove-orphans --volumes

rm "$PWD/web-client/ozon/base/data/user.json"
rm -r "$PWD/scripts/init_db.js"
rm -r "$PWD/scripts"
rm -r "$PWD/mdbdata"
