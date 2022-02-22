#!/bin/bash
source .env
CURRPATH=${PWD}
if [ "${API_USER_KEY}" = "" ]; then
  echo "set .env param API_USER_KEY=$(uuidgen)"
  echo "and repet command"
  exit 0
fi
./init.sh
echo "setup coplete"
cd $CURRPATH
if [ -e "$PWD/docker-compose-custom.yml" ]; then
  echo "setup compose custom"
  docker-compose -f docker-compose-custom.yml -p ${STACK} --profile all stop
  docker-compose -f docker-compose-custom.yml -p ${STACK} --profile all --compatibility up --force-recreate  --always-recreate-deps --detach --build
else
  echo "setup compose ${APP_NAME}"
  docker-compose -f docker-compose.yml --env-file .env -p ${STACK} --profile all stop
  docker-compose -f docker-compose.yml --env-file .env -p ${STACK} --profile all --compatibility up --force-recreate --always-recreate-deps --detach --build
fi
#for $val in $APPS; do # resolve $SOURCE until the file is no longer a symlink
#  cd $CURRPATH"/web-client/inrim/app_$val/docker"
#  ./build.sh $CURRPATH
#done