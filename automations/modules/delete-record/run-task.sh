#!/bin/bash
source /automations/modules/.env
curl -X 'GET' 'http://client:8526/client/run/clean-app' -H 'accept: application/json' -H 'apitoken:'$API_USER_KEY
