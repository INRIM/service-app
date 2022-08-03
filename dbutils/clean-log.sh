#!/bin/bash
rm /srv/mci/clean-log.log

exec >> /srv/mci/clean-log.log 2>&1

echo "CLEAN LOG AND DOCKER"

rm -f ../automations/modules/main-scheduler/log/run_task.log*
rm -f ../automations/modules/calendar-task/logs/*.log


