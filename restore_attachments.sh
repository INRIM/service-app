#!/bin/bash
if [ -z $1 ]; then
  echo "usage: restore_attachments.sh user@remote:/path/service/uploads"
  exit 0
fi
source .env
PRJPWD="$PWD"
echo "clean ${PRJPWD}/uploads"
rm -rf ${PRJPWD}/uploads
echo "copy from $1 to  ${PRJPWD}/uploads"
scp -r $1  ${PRJPWD}/uploads
echo "attachments restore: Done."
