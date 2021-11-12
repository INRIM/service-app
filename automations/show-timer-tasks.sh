#!/bin/bash
echo "Core timer:"
systemctl status  main-scheduler.timer
echo ""
systemctl status  clean-records.timer
echo ""
echo "List all timer ->  systemctl list-timers"
systemctl list-timers

