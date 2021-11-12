#!/bin/bash
TITLE=$1
NAME=$2
CALENDAR=$3
TASK_TYPE=$4
SERVICE='
[Unit]
Description='$TITLE'

[Service]
Type=oneshot
WorkingDirectory=/automations/modules/calendar-task
ExecStart=/automations/modules/calendar-task/run-task.sh "'$NAME'"
'
TIMER='
[Unit]
Description='$TITLE' Timer

[Timer]
Unit='$NAME'.service
OnCalendar='$CALENDAR'

[Install]
WantedBy=timers.target
'
FILE=/etc/systemd/system/$NAME.timer
if [ ! -f "$FILE" ]; then
  echo "${TIMER}" >  /etc/systemd/system/$NAME.timer
  echo "${SERVICE}" >  /etc/systemd/system/$NAME.service
  systemd-run systemctl enable $NAME.timer
  systemd-run systemctl start $NAME.timer
fi
#systemctl list-timers
# ll /etc/systemd/system/