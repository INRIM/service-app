#!/bin/bash
if [ ! -e "$PWD/.env" ]; then
     echo "no .env file found"
fi
source ${PWD}/.env
if [ "$API_USER_KEY" = "" ]; then
  echo "set .env param API_USER_KEY=$(uuidgen)"
  echo "and repet command"
fi
echo "setup ports"
if [ -z "${MONGO_PORT}" ]; then
   export MONGO_PORT=27018
fi
if [ -z "${SERVER_PORT}" ]; then
   export SERVER_PORT=8225
fi
if [ -z "${CLIENT_PORT}" ]; then
   export CLIENT_PORT=8526
fi
if [ -z "${COOKPIT_PORT}" ]; then
   export COOKPIT_PORT=9090
fi
if [ -z "${STACK}" ]; then
   export STACK="service-app"
fi
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
     sh setup_db.sh
fi
echo "setup basic user data"
if [ ! -e "$PWD/web-client/ozon/base/data/user.json" ]; then
     sh setup_user.sh
fi
cp ${PWD}/.env ${PWD}/automations/modules/.env
echo "setup basic nginx.conf"
if [ ! -e "$PWD/nginx.conf" ]; then
  NGINX_CONF='user  nginx;
worker_rlimit_nofile 8192;
events {
    worker_connections  4096;
}
http {
        server {
              listen '$SERVER_PORT';
              location / {
                proxy_pass http://backend:8225;
              }
        }
        server {
              listen '$CLIENT_PORT';
              location / {
                proxy_pass http://client:8526;
              }
        }
}
stream {
    server {
        listen  '$MONGO_PORT' so_keepalive=on;
        proxy_connect_timeout 2s;
        proxy_pass    stream_mongo_backend;
        proxy_timeout 10m;
    }

    upstream stream_mongo_backend {
         server 127.0.0.1:27017;
    }

}

  '
  echo "${NGINX_CONF}" >  nginx.conf
fi

echo "init coplete"