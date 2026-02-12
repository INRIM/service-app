#!/bin/bash
source .env
echo "dump db $MONGO_DB"
CMD="mongodump -u $MONGO_USER -p xxxxx -d $MONGO_DB --out /dump"
echo $CMD
docker exec ${STACK}-database-1 bash -c "${CMD}"
echo "make project: Done."
