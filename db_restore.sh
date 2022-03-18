#!/bin/bash
source .env
echo "Restore  stack ${STACK} DB $MONGO_DB"
CMD="mongorestore -u ${MONGO_USER} -p ${MONGO_PASS} -d ${MONGO_DB} /dump/${MONGO_DB}"
docker exec ${STACK}_database_1 /bin/bash -c "$CMD"
echo "make project: Done."