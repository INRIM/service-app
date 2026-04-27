#!/bin/bash
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "usage: db_restore.sh user@remote:/path/service/dump"
  exit 1
fi

source .env

PRJPWD="$PWD"
CONTAINER="${STACK}-database-1"

read -rp "Inserisci email da impostare in mail_template.recipient: " CHECK_EMAIL

if ! printf '%s' "$CHECK_EMAIL" | grep -Eq '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'; then
  echo "Email non valida: $CHECK_EMAIL"
  exit 1
fi

rm -rf "${PRJPWD}/dump/${MONGO_DB}"
mkdir -p "${PRJPWD}/dump"

echo "copy from $1/${MONGO_DB} to ${PRJPWD}/dump/${MONGO_DB}"
scp -r "$1/${MONGO_DB}" "${PRJPWD}/dump/${MONGO_DB}"

echo "Restore stack ${STACK} DB ${MONGO_DB}"

RESTORE_CMD='mongorestore --drop -u "'"${MONGO_USER}"'" -p "'"${MONGO_PASS}"'" --nsInclude="'"${MONGO_DB}"'.*" /dump'
echo "$RESTORE_CMD"
echo ""
docker exec "$CONTAINER" /bin/bash -lc "$RESTORE_CMD"

echo "Restore DB ${MONGO_DB}: OK"
echo "Aggiorno mail_template.recipient con ${CHECK_EMAIL}"

UPDATE_CMD='mongosh --quiet \
  -u "'"${MONGO_USER}"'" \
  -p "'"${MONGO_PASS}"'" \
  --authenticationDatabase admin \
  "'"${MONGO_DB}"'" \
  --eval "
    const email = process.env.CHECK_EMAIL;
    const coll = db.getCollection(\"mail_template\");

    const exists = coll.countDocuments({});
    if (exists === 0) {
      printjson({ ok: 0, error: \"collection mail_template vuota o inesistente\" });
      quit(2);
    }

    const res = coll.updateMany({}, { \$set: { recipient: email } });
    printjson({
      ok: 1,
      matchedCount: res.matchedCount,
      modifiedCount: res.modifiedCount
    });

    const wrong = coll.countDocuments({ recipient: { \$ne: email } });
    const updated = coll.countDocuments({ recipient: email });

    printjson({
      verify: {
        expectedRecipient: email,
        updatedDocs: updated,
        wrongDocs: wrong
      }
    });

    if (wrong > 0 || updated === 0) {
      quit(3);
    }
  "'

docker exec -e CHECK_EMAIL="$CHECK_EMAIL" "$CONTAINER" /bin/bash -lc "$UPDATE_CMD"

echo "Verifica update mail_template.recipient: OK"