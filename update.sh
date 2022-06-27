#!/bin/bash
echo "update project"
source .env
# openssl rand -hex 16
if [ -z $1 ]; then
  echo "usage: update.sh  profiles  [apps, automation, all]"
  echo "apps: restart only webapps and mongodb"
  echo "all: restart all system webapps, mongodb,automation, redis"
  exit 0
fi
if [ "$1" == "automation" ]; then
  docker-compose -f docker-compose.yml -p ${STACK} --profile all stop
  docker-compose -f docker-compose.yml -p ${STACK} --profile automation up --force-recreate  --always-recreate-deps -d --build
  docker-compose -f docker-compose.yml -p ${STACK} --profile all  up -d
else
  docker-compose -f  docker-compose.yml -p ${STACK} --profile $1 stop
  docker-compose -f  docker-compose.yml -p ${STACK} --profile $1 up -d
fi

echo "make project: Done."
