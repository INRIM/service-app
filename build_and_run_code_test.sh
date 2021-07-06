#!/bin/bash
if [ -d "$PWD/app/ozon/core/libs" ]; then
      git -C "$PWD/app/ozon/core/libs" pull
  else
      git -C "$PWD/app/ozon/core" clone https://gitlab.ininrim.it/inrimsi/microservices-libs/base-libs.git libs
fi
if [ ! -f ".env-test" ]; then
    echo ".env-test File not found!"
    exit 0
fi
docker-compose -f docker-compose.yml stop
docker-compose -f docker-compose.yml -p inrim-service-app up --force-recreate --detach --remove-orphans --build  test-api-inrim-forms
docker network create moduli_net
docker network connect moduli_net inrim-moduli-backend_test-api-inrim-forms_1
docker exec -ti inrim-moduli-backend_test-api-inrim-forms_1 pytest .;