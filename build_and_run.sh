#!/bin/bash
source ${PWD}/.env
CURRPATH=${PWD}
#./init.sh
echo "Update"
docker-compose -f  docker-compose.yml -p ${APP_CODE}  --profile core-only stop
docker-compose -f  docker-compose.yml --env-file .env -p ${APP_CODE} --profile core-only --compatibility up -d
