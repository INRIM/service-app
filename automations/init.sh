#!/bin/bash
#add here the units to check
# use systemd-analyze calendar 0/6:*:*
rm -f /lib/systemd/system/multi-user.target.wants/getty*
mkdir /etc/systemd/system/app-services
mkdir /etc/systemd/system/app-tasks
cd /automations/modules/delete-record; sh add-unit.sh
cd /automations/modules/main-scheduler; sh add-unit.sh
cd /automations
APP_MODULES=${APP_MODULES:-/automations/app_modules.sh}
echo "Checking for script for $APP_MODULES"
if [ -f $APP_MODULES ] ; then
    echo "Running script for $APP_MODULES"
    . "$APP_MODULES"
else
    echo "There is no script for $APP_MODULES"
fi
# TODO https://github.com/Josef-Friedrich/check_systemd
