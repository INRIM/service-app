#!/bin/bash
docker-compose -f docker-compose.yml -p service-app stop
rm "$PWD/backend/ozon/base/data/user.json"
rm -r "$PWD/scripts/init_db.js"
docker rm -fv service-appsh cle
docker rmi -f mongo-service-app
docker rmi -f python3.8.services-app
docker rmi -f python3.8.client-services-app