#!/bin/bash
source .env
echo "Restore db $MONGO_DB"
CMD="mongorestore -u ${MONGO_USER} -p ${MONGO_PASS} -d ${MONGO_DB} /dump/${MONGO_DB}"
docker exec mci-database-1 bash -c "$CMD"
echo "make project: Done."