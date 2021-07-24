#!/bin/bash
docker-compose -f docker-compose.yml -p service-app stop
docker-compose -f docker-compose.yml -p service-app start