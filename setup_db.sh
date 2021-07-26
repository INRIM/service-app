source .env
DATA='
db.createUser({
  user: "'$MONGO_INITDB_ROOT_USERNAME'",
  pwd:  "'$MONGO_INITDB_ROOT_PASSWORD'",
  roles: [ { role: "readWrite", db: "'$MONGO_INITDB_DATABASE'" } ]
});'
echo "${DATA}" > scripts/init_db.js