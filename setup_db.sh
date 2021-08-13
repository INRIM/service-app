source .env
DATA='
db.createUser({
  user: "'$MONGO_USER'",
  pwd:  "'$MONGO_PASS'",
  roles: [ { role: "readWrite", db: "'$MONGO_DB'" } ]
});'
echo "${DATA}" > scripts/init_db.js