#!/bin/bash
source ${PWD}/.env
CURRPATH=${PWD}
./init.sh
echo "Compose eand Run"
if [ -e "$PWD/docker-compose-custom.yml" ]; then
  docker-compose -f  docker-compose.yml -f docker-compose-custom.yml -p ${STACK} --profile core-only stop
  docker-compose -f docker-compose.yml  -f docker-compose-custom.yml -p ${STACK} --profile core-only up -d
else
#docker-compose -f  docker-compose.yml -p ${STACK} --profile core-only stop
docker-compose -f  docker-compose.yml --env-file .env -p ${STACK} --profile core-only up -d
fi