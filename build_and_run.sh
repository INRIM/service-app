#!/bin/bash
source .env
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
docker-compose -f docker-compose.yml -p service-app stop
docker-compose -f docker-compose.yml -p service-app up --force-recreate  --always-recreate-deps --detach --remove-orphans --build