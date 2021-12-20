#!/bin/bash
#add here the units to check
# use systemd-analyze calendar 0/6:*:*
rm -f /lib/systemd/system/multi-user.target.wants/getty*
mkdir /etc/systemd/system/app-services
mkdir /etc/systemd/system/app-tasks
cd /automations/modules/delete-record; sh add-unit.sh
cd /automations/modules/main-scheduler; sh add-unit.sh
cd /automations
# TODO https://github.com/Josef-Friedrich/check_systemd
