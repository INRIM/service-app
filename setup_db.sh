#!/bin/bash
source ${PWD}/.env
DATA='
db.createUser({
  user: "'$MONGO_USER'",
  pwd:  "'$MONGO_PASS'",
  roles: [ { role: "readWrite", db: "'$MONGO_DB'" },{ role: "readWrite", db: "admin" } ]
});'
echo "${DATA}" > scripts/init_db.js