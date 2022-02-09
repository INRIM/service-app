#!/bin/bash
source .env
echo "dump db $MONGO_DB"
CMD="mongodump -u $MONGO_USER -p $MONGO_PASS -d $MONGO_DB --out /dump"
echo CMD
docker exec mci-database-1 bash -c "${CMD}"
echo "make project: Done."
