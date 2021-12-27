#!/bin/bash
source ${PWD}/.env
CURRPATH=${PWD}
if [ "${API_USER_KEY}" = "" ]; then
  echo "set .env param API_USER_KEY=$(uuidgen)"
  echo "and repet command"
  exit 0
fi
./init.sh
echo "setup coplete"
if [ -e "$PWD/docker-compose-custom.yml" ]; then
  echo "setup compose custom"
  docker-compose -f docker-compose-custom.yml -p ${STACK} --profile all stop
  docker-compose -f docker-compose-custom.yml -p ${STACK} --profile all --compatibility up --force-recreate  --always-recreate-deps --detach --build
else
  echo "setup compose"
  docker-compose -f docker-compose.yml --env-file .env -p ${STACK} --profile all stop
  docker-compose -f docker-compose.yml --env-file .env -p ${STACK} --profile all --compatibility up --force-recreate --always-recreate-deps --detach --build
fi
