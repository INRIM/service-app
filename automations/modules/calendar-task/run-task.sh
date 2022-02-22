#!/bin/bash
#exec >> /automations/modules/calendar-task/logs/$1.log 2>&1
source /automations/modules/.env
echo "Execute: -X 'POST' 'http://client:8526/client/run/calendar_tasks/$1' -H 'accept: application/json' -H 'apitoken:$API_USER_KEY'"
echo ""
curl -X 'POST' 'http://client:8526/client/run/calendar_tasks/'"$1" -H 'accept: application/json' -H 'apitoken:'"$API_USER_KEY"
echo "Done"