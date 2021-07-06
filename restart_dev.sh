#!/bin/bash
docker-compose -f docker-compose.yml -p inrim-service-app stop
docker-compose -f docker-compose.yml -p inrim-service-app start