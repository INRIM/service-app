#!/bin/bash
echo "pause service $1"
source /automations/modules/.env
systemctl start $1.timer
