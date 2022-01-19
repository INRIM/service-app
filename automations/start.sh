#!/bin/bash
#add here the units to check
# use systemd-analyze calendar 0/6:*:*
cd automations
./init.sh
exec /lib/systemd/systemd