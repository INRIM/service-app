#!/bin/bash
TITLE=$1
NAME=$2
CALENDAR=$3
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
echo "${SERVICE}" >  /etc/systemd/system/$NAME.service
echo "${TIMER}" >  /etc/systemd/system/$NAME.timer
systemctl enable $NAME.timer
systemctl start $NAME.timer
