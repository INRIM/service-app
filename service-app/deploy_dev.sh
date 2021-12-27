#!/bin/bash
echo "make project"
# openssl rand -hex 16
# uuidge() for API_USER_KEY
PRJPWD="$PWD"
if [ -d "$PRJPWD/service-app" ]; then
      cd ${PRJPWD}/service-app
      ./stop.sh
      cd ${PRJPWD}
      git -C "$PRJPWD/service-app" pull
  else
      git -C ${PRJPWD} clone git@gitlab.ininrim.it:inrimsi/microservice/services-apps/service-app.git service-app
fi
if [ -d "$PRJPWD/service-app/backend/inrim" ]; then
      git -C "$PRJPWD/service-app/backend/inrim" pull
  else
      git -C "$PRJPWD/service-app/backend/" clone git@gitlab.ininrim.it:inrimsi/microservice/services-apps/plugins/backend/inrim.git inrim
fi
if [ -d "$PRJPWD/service-app/web-client/inrim" ]; then
      git -C "$PRJPWD/service-app/web-client/inrim" pull
  else
      git -C "$PRJPWD/service-app/web-client" clone git@gitlab.ininrim.it:inrimsi/microservice/services-apps/plugins/webclient/inirm.git inrim
fi
cp -rf ${PRJPWD}/build_config/* ${PRJPWD}/service-app/.
cp -rf ${PRJPWD}/build_config_dev/* ${PRJPWD}/service-app/.
cd ${PRJPWD}/service-app/
./deploy.sh
cd $PRJPWD
if [ -d "/etc/nginx" ]; then
  if [ ! -e "/etc/nginx/sites-available/service-mci.docker3.ininrim.it" ]; then
    echo "Configure Ngnix ..."
    sudo cp service-mci.docker3.ininrim.it /etc/nginx/sites-available/service-mci.docker3.ininrim.it
    sudo cp api-service-mci.docker3.ininrim.it /etc/nginx/sites-available/api-service-mci.docker3.ininrim.it
    cd /etc/nginx/sites-enabled/
    sudo ln -s /etc/nginx/sites-available/service-mci.docker3.ininrim.it
    sudo ln -s /etc/nginx/sites-available/api-service-mci.docker3.ininrim.it
    sudo systemctl restart nginx
  fi
fi
echo "make project: Done."
