#!/bin/bash
source /automations/modules/.env
echo "pause service $1"
systemctl stop $1.timer
systemctl stop $1.service
echo "remove service $1"
systemctl disable $1.timer
systemctl disable $1.service
rm -f /etc/systemd/system/$1.*
rm -f /etc/systemd/system/timers.target.wants/$1.*
systemctl daemon-reload
systemctl reset-failed
echo "removed service $1"
