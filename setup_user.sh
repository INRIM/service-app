source .env
USER='
[
  {
    "rec_name":"'$ADMIN_USERNAME'",
    "uid":"'$ADMIN_USERNAME'",
    "password":"'$ADMIN_PASSWORD'",
    "token":"'$(uuidgen)'",
    "is_admin":true,
    "is_bot":true,
    "nome":"Admin",
    "mail":"admin@admin.it"
    "cognome":"Admin",
    "full_name":"Admin Admin",
    "user_function":"user"
  }
]
'
echo "${USER}" > backend/ozon/base/data/user.json