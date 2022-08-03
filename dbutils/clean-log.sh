#!/bin/bash

echo "CLEAN LOG AND DOCKER"

rm -f ../automations/modules/main-scheduler/log/run_task.log*
rm -f ../automations/modules/calendar-task/logs/*.log


