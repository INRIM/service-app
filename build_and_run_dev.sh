#!/bin/bash
echo "Prepare backend"
#if [ -d "$PWD/backend/inrim" ]; then
#      git -C "$PWD/backend/inrim" pull
#  else
#      git -C "$PWD/backend" clone https://gitlab.ininrim.it/inrimsi/microservices-libs/async-service-libs.git inrim
#fi
#if [ -d "$PWD/backend/inrim/libs" ]; then
#      git -C "$PWD/backend/inrim/libs" pull
#  else
#      git -C "$PWD/backend/inrim" clone https://gitlab.ininrim.it/inrimsi/microservices-libs/async-service-libs.git libs
#fi
#if [ ! -f ".env" ]; then
#    echo ".env File not found!"
#    exit 0
#fi
## Client Web
#echo "Prepare web Client"
#if [ -d "$PWD/web-client/core/themes/italia" ]; then
#      git -C "$PWD/web-client/core/themes/italia" pull
#  else
#      git -C "$PWD/web-client/core/themes" clone https://gitlab.ininrim.it/inrimsi/microservices-libs/form-theme-italia.git italia
#fi
#if [ ! -f ".env-client" ]; then
#    echo ".env-client File not found!"
#    exit 0
#fi
echo "setup mongo"
if [ -z "${MONGO_INITDB_DATABASE}" ]; then
   echo "MONGO_INITDB_DATABASE env var not set and reuired!"
   exit 0
fi
if [ -z "${MONGO_INITDB_ROOT_USERNAME}" ]; then
   echo "MONGO_INITDB_ROOT_USERNAME env var not set and reuired!"
   exit 0
fi
if [ -z "${MONGO_INITDB_ROOT_PASSWORD}" ]; then
   echo "MONGO_INITDB_ROOT_PASSWORD env var not set and reuired!"
   exit 0
fi
if [ -z "${ADMIN_USERNAME}" ]; then
   echo "ADMIN_USERNAME env var not set and reuired!"
   exit 0
fi
if [ -z "${ADMIN_PASSWORD}" ]; then
   echo "ADMIN_PASSWORD env var not set and reuired!"
   exit 0
fi
if [ ! -e "$PWD/scripts/init_db.js" ]; then
     mkdir scripts
     sh setup_db.sh
fi
if [ ! -e "$PWD/backend/ozon/base/data/user.json" ]; then
     sh setup_user.sh
fi
echo "Run Build"
docker-compose -f docker-compose.yml -p inrim-service-app stop
docker-compose -f docker-compose.yml -p inrim-service-app up --force-recreate  --always-recreate-deps --remove-orphans --build