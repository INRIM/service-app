USER='
[
  {
    "uid":"'$ADMIN_USERNAME'",
    "password":"'$ADMIN_PASSWORD'",
    "token":"'$(uuidgen)'",
    "is_admin":true,
    "is_bot":true,
    "first_name":"Admin",
    "last_name":"Admin"
  }
]
'
echo "${USER}" > backend/ozon/base/data/user.json