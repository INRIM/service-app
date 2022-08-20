#!/bin/bash
if [ -z $1 ]; then
  echo "usage: db_restore.sh user@remote:/path/dervice/dump"
  exit 0
fi
source .env
echo "copy from $1/${MONGO_DB} to  dump/${MONGO_DB}"
scp -r $1/${MONGO_DB} dump/${MONGO_DB}
echo "Restore  stack ${STACK} DB $MONGO_DB"
CMD="mongorestore --drop -u ${MONGO_USER} -p ${MONGO_PASS} -d ${MONGO_DB} /dump/${MONGO_DB}"
docker exec ${STACK}-database-1 /bin/bash -c "$CMD"
echo "make project: Done."
