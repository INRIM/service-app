#!/bin/bash
if [ ! -e ".env" ]; then
     echo "no .env file found"
fi
source .env
echo "setup mongo"
if [ -z "${MONGO_DB}" ]; then
   echo "MONGO_DB env var not set and required!"
   exit 0
fi
if [ -z "${MONGO_USER}" ]; then
   echo "MONGO_USER env var not set and required!"
   exit 0
fi
if [ -z "${MONGO_PASS}" ]; then
   echo "MONGO_PASS env var not set and required!"
   exit 0
fi
if [ -z "${ADMIN_USERNAME}" ]; then
   echo "ADMIN_USERNAME env var not set and required!"
   exit 0
fi
if [ -z "${ADMIN_PASSWORD}" ]; then
   echo "ADMIN_PASSWORD env var not set and required!"
   exit 0
fi
if [ ! -e "$PWD/scripts/init_db.js" ]; then
     mkdir scripts
     ./setup_db.sh
fi
echo "setup basic user data"
./setup_user.sh
cp config_system.json ./automations/modules/config.json
cp .env ./automations/modules/.env
echo "init coplete"