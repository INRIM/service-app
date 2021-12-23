#!/bin/bash
source ${PWD}/.env
CURRPATH=${PWD}
./init.sh
if [ -e "$PWD/docker-compose-custom.yml" ]; then
  docker-compose -f docker-compose-custom.yml -p ${STACK} --profile all stop
  docker-compose -f docker-compose-custom.yml -p ${STACK} --profile all up --force-recreate  --always-recreate-deps --detach --remove-orphans --build
else
  docker-compose -f docker-compose.yml -p ${STACK} --profile all stop
  docker-compose -f docker-compose.yml --env-file .env -p ${STACK} --profile all up --force-recreate  --always-recreate-deps --detach --remove-orphans --build
fi
