#!/bin/bash
cp clean-records.service  /lib/systemd/system/clean-records.service
cp clean-records.timer /lib/systemd/system/clean-records.timer
cd /etc/systemd/system/app-services
ln -s /lib/systemd/system/clean-records.service .
cd /etc/systemd/system/timers.target.wants
ln -s /lib/systemd/system/clean-records.timer .
chmod 777 clean-records.timer
#systemctl list-units --all clean-records.*