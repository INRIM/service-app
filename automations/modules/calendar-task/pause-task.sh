#!/bin/bash
echo "pause service $1"
source /automations/modules/.env
systemctl stop $1.timer
systemctl stop $1.service