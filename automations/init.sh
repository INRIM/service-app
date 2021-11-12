#!/bin/bash
#add here the units to check
# use systemd-analyze calendar 0/6:*:*
mkdir /etc/systemd/system/app-services
mkdir /etc/systemd/system/app-tasks
mkdir /automations/modules/main-scheduler/log
mkdir /automations/modules/calendar-task/logs
cd /automations/modules/delete-record; sh add-unit.sh
cd /automations/modules/main-scheduler; sh add-unit.sh
cd /automations
# TODO https://github.com/Josef-Friedrich/check_systemd
