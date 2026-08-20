#!/usr/bin/env bash
# Provisioning Keycloak per la demo: realm + client confidenziale + 4 utenti
# (admin/admin, user/user, operator/operator, manager/manager). Idempotente.
# Config letta dall'ambiente (vedi run_demo.sh), con default = demo/.env.demo
# + demo/.env.client-demo per uso standalone.
#
# Stampa su stdout due righe:
#   KEYCLOAK_CLIENT_SECRET=<value>            (client web, auth-code)
#   SCHEDULER_OAUTH_CLIENT_SECRET=<value>      (client M2M calendar-scheduler)
#
# Richiede: curl, jq
set -euo pipefail

KC="${KEYCLOAK_SERVER_URL_PUBLIC:-http://localhost:8081}"
KC_ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
KC_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-b6a7e4b1356323d5}"
REALM="${KEYCLOAK_REALM:-backend}"
CLIENT_ID="${KEYCLOAK_CLIENT_ID:-backend-web}"
SITE_URL="${SITE_URL:-http://localhost:4200}"
REDIRECT_URI="${SITE_URL}/auth/callback"
WEB_ORIGIN="${SITE_URL}"
SCHEDULER_CLIENT_ID="${SCHEDULER_OAUTH_CLIENT_ID:-calendar-scheduler}"
# URL che KEYCLOAK chiama quando una sessione termina (logout utente,
# logout amministrativo, scadenza idle). Va risolto DALLA rete dei
# container, non dal browser: e' il server Keycloak a fare il POST.
BACKCHANNEL_LOGOUT_URL="${BACKCHANNEL_LOGOUT_URL:-http://ozon-env-app:8000/auth/backchannel-logout}"
AUDIENCE="${OZON_TOKEN_AUDIENCE:-${APP_CODE:-demo}}"

USERS=(admin user operator manager)  # password == username

log() { echo "$@" >&2; }

ensure_audience_mapper() {
    local client_uuid="$1"
    local client_id="$2"
    local mapper_name="${AUDIENCE}-audience"
    local mappers_url="${KC}/admin/realms/${REALM}/clients/${client_uuid}/protocol-mappers/models"
    local mapper_id
    local payload

    payload="$(jq -n \
        --arg name "$mapper_name" \
        --arg audience "$AUDIENCE" \
        '{
            name:$name,
            protocol:"openid-connect",
            protocolMapper:"oidc-audience-mapper",
            consentRequired:false,
            config:{
                "included.custom.audience":$audience,
                "id.token.claim":"false",
                "access.token.claim":"true",
                "introspection.token.claim":"true"
            }
        }')"
    mapper_id="$(curl -fs "${auth[@]}" "$mappers_url" | jq -r \
        --arg name "$mapper_name" \
        '.[] | select(.name == $name and .protocolMapper == "oidc-audience-mapper") | .id' \
        | head -n 1)"

    if [[ -n "$mapper_id" ]]; then
        curl -fs -o /dev/null "${auth[@]}" -X PUT "${mappers_url}/${mapper_id}" \
            -d "$(echo "$payload" | jq --arg id "$mapper_id" '. + {id:$id}')"
        log "audience '${AUDIENCE}' updated for client '${client_id}'"
    else
        curl -fs -o /dev/null "${auth[@]}" -X POST "$mappers_url" -d "$payload"
        log "audience '${AUDIENCE}' enabled for client '${client_id}'"
    fi
}

ensure_backchannel_logout() {
    local client_uuid="$1"
    local client_id="$2"
    # Senza questo, l'app non ha modo di sapere che una sessione e' stata
    # chiusa: verifica il JWT solo localmente, quindi un token gia'
    # emesso resta valido fino alla sua scadenza anche dopo il logout.
    curl -fs -o /dev/null "${auth[@]}" -X PUT \
        "${KC}/admin/realms/${REALM}/clients/${client_uuid}" \
        -d "$(jq -n --arg url "$BACKCHANNEL_LOGOUT_URL" \
            --arg post_logout "${SITE_URL}/*" \
            '{attributes:{
                "backchannel.logout.url":$url,
                "backchannel.logout.session.required":"true",
                "backchannel.logout.revoke.offline.tokens":"false",
                "post.logout.redirect.uris":$post_logout
            }}')"
    log "backchannel logout '${BACKCHANNEL_LOGOUT_URL}' set for client '${client_id}'"
}

TOKEN="$(curl -fs -X POST "${KC}/realms/master/protocol/openid-connect/token" \
    --data-urlencode "grant_type=password" \
    --data-urlencode "client_id=admin-cli" \
    --data-urlencode "username=${KC_ADMIN_USER}" \
    --data-urlencode "password=${KC_ADMIN_PASSWORD}" \
    | jq -r '.access_token')"

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
    log "impossibile ottenere il token admin da Keycloak"
    exit 1
fi

auth=(-H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json")

# --- realm ---
if curl -fs -o /dev/null "${auth[@]}" "${KC}/admin/realms/${REALM}"; then
    log "realm '${REALM}' already exists"
else
    curl -fs -o /dev/null "${auth[@]}" -X POST "${KC}/admin/realms" \
        -d "{\"realm\":\"${REALM}\",\"enabled\":true}"
    log "realm '${REALM}' created"
fi

# --- client ---
CLIENT_UUID="$(curl -fs "${auth[@]}" "${KC}/admin/realms/${REALM}/clients?clientId=${CLIENT_ID}" | jq -r '.[0].id // empty')"
if [[ -n "$CLIENT_UUID" ]]; then
    log "client '${CLIENT_ID}' already exists"
    curl -fs -o /dev/null "${auth[@]}" -X PUT "${KC}/admin/realms/${REALM}/clients/${CLIENT_UUID}" \
        -d "{\"redirectUris\":[\"${REDIRECT_URI}\"],\"webOrigins\":[\"${WEB_ORIGIN}\"]}"
else
    LOCATION="$(curl -fsi "${auth[@]}" -X POST "${KC}/admin/realms/${REALM}/clients" -d "$(jq -n \
        --arg cid "$CLIENT_ID" --arg redirect "$REDIRECT_URI" --arg origin "$WEB_ORIGIN" \
        '{clientId:$cid, protocol:"openid-connect", publicClient:false, standardFlowEnabled:true, directAccessGrantsEnabled:false, serviceAccountsEnabled:false, redirectUris:[$redirect], webOrigins:[$origin]}')" \
        | grep -i '^location:')"
    CLIENT_UUID="${LOCATION##*/}"
    CLIENT_UUID="${CLIENT_UUID//$'\r'/}"
    log "client '${CLIENT_ID}' created"
fi

SECRET="$(curl -fs "${auth[@]}" "${KC}/admin/realms/${REALM}/clients/${CLIENT_UUID}/client-secret" | jq -r '.value')"
ensure_audience_mapper "$CLIENT_UUID" "$CLIENT_ID"
ensure_backchannel_logout "$CLIENT_UUID" "$CLIENT_ID"

# --- client M2M per calendar-scheduler (client_credentials, service account) ---
SCHED_UUID="$(curl -fs "${auth[@]}" "${KC}/admin/realms/${REALM}/clients?clientId=${SCHEDULER_CLIENT_ID}" | jq -r '.[0].id // empty')"
if [[ -n "$SCHED_UUID" ]]; then
    log "client '${SCHEDULER_CLIENT_ID}' already exists"
else
    LOCATION="$(curl -fsi "${auth[@]}" -X POST "${KC}/admin/realms/${REALM}/clients" -d "$(jq -n \
        --arg cid "$SCHEDULER_CLIENT_ID" \
        '{clientId:$cid, protocol:"openid-connect", publicClient:false, standardFlowEnabled:false, directAccessGrantsEnabled:false, serviceAccountsEnabled:true}')" \
        | grep -i '^location:')"
    SCHED_UUID="${LOCATION##*/}"
    SCHED_UUID="${SCHED_UUID//$'\r'/}"
    log "client '${SCHEDULER_CLIENT_ID}' created (service account)"
fi
SCHED_SECRET="$(curl -fs "${auth[@]}" "${KC}/admin/realms/${REALM}/clients/${SCHED_UUID}/client-secret" | jq -r '.value')"
ensure_audience_mapper "$SCHED_UUID" "$SCHEDULER_CLIENT_ID"

# service-account-<clientId> deve essere admin per app_code=demo (group_users),
# altrimenti l'ACL nega le scritture del backend all'endpoint /client/run/*.
SCHED_SA_USERNAME="service-account-${SCHEDULER_CLIENT_ID}"
if ! curl -fs "${auth[@]}" "${KC}/admin/realms/${REALM}/users?username=${SCHED_SA_USERNAME}&exact=true" | jq -e '.[0].id' >/dev/null; then
    log "warning: utente service account '${SCHED_SA_USERNAME}' non trovato (verra' creato al primo avvio del client M2M)"
fi

# --- users ---
for username in "${USERS[@]}"; do
    profile="$(jq -n --arg fn "${username^}" --arg email "${username}@demo.local" \
        '{firstName:$fn, lastName:"Demo", email:$email, emailVerified:true, requiredActions:[]}')"

    USER_ID="$(curl -fs "${auth[@]}" "${KC}/admin/realms/${REALM}/users?username=${username}&exact=true" | jq -r '.[0].id // empty')"
    if [[ -n "$USER_ID" ]]; then
        log "user '${username}' already exists"
        curl -fs -o /dev/null "${auth[@]}" -X PUT "${KC}/admin/realms/${REALM}/users/${USER_ID}" -d "$profile"
    else
        LOCATION="$(curl -fsi "${auth[@]}" -X POST "${KC}/admin/realms/${REALM}/users" \
            -d "$(echo "$profile" | jq --arg u "$username" '. + {username:$u, enabled:true}')" \
            | grep -i '^location:')"
        USER_ID="${LOCATION##*/}"
        USER_ID="${USER_ID//$'\r'/}"
        log "user '${username}' created"
    fi

    curl -fs -o /dev/null "${auth[@]}" -X PUT "${KC}/admin/realms/${REALM}/users/${USER_ID}/reset-password" \
        -d "{\"type\":\"password\",\"value\":\"${username}\",\"temporary\":false}"
    log "  password set for '${username}'"
done

echo "KEYCLOAK_CLIENT_SECRET=${SECRET}"
echo "SCHEDULER_OAUTH_CLIENT_SECRET=${SCHED_SECRET}"
