cp main-scheduler.service  /lib/systemd/system/main-scheduler.service
cp main-scheduler.timer /lib/systemd/system/main-scheduler.timer
cd /etc/systemd/system/app-services
ln -s /lib/systemd/system/main-scheduler.service .
cd /etc/systemd/system/timers.target.wants
ln -s /lib/systemd/system/main-scheduler.timer .
chmod 777 main-scheduler.timer
#systemctl list-units --all main-scheduler.*
#systemctl status $SNAME.service
#journalctl -S today -u $SNAME.service