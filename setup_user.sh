source .env
KEY=$(uuidgen)
USER='
[
  {
    "rec_name":"'$ADMIN_USERNAME'",
    "uid":"'$ADMIN_USERNAME'",
    "password":"'$ADMIN_PASSWORD'",
    "token":"'$API_USER_KEY'",
    "is_admin":true,
    "is_bot":true,
    "nome":"Admin",
    "mail":"admin@none.none",
    "cognome":"Admin",
    "full_name":"Admin Admin",
    "user_function":"user"
  }
]
'
echo "${USER}" > backend/ozon/base/data/user.json