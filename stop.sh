#!/bin/bash
source ${PWD}/.env
echo "Stop service"
docker-compose -f docker-compose.yml -p service-app stop
