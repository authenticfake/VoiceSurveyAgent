#!/usr/bin/env bash
set -euo pipefail

: "${BASE:=http://127.0.0.1:8880}"
: "${TOKEN:?Devi esportare TOKEN (Bearer token)}"

hdr_auth=(-H "Authorization: Bearer $TOKEN")
hdr_json=(-H "Content-Type: application/json")

fail() { echo "ERROR: $*" >&2; exit 1; }

curl_json() {
  # usage: curl_json METHOD PATH JSON_BODY(optional)
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local url="$BASE$path"

  if [[ -n "$body" ]]; then
    curl -s -w '\n%{http_code}' -X "$method" "$url" "${hdr_auth[@]}" "${hdr_json[@]}" -d "$body"
  else
    curl -s -w '\n%{http_code}' -X "$method" "$url" "${hdr_auth[@]}"
  fi
}

print_resp() {
  local resp="$1"
  local body code
  body="$(printf "%s" "$resp" | sed '$d')"
  code="$(printf "%s" "$resp" | tail -n 1)"
  echo "HTTP=$code"
  if [[ -n "$body" ]]; then
    echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
  else
    echo "(no body)"
  fi
  echo
}

# 1) Check token (quick call that requires auth)
echo "== Token check =="
resp="$(curl_json GET "/api/campaigns" || true)"
code="$(printf "%s" "$resp" | tail -n 1)"
if [[ "$code" == "401" ]]; then
  echo "HTTP=401"
  echo "TOKEN scaduto. Rigenera TOKEN e rilancia."
  echo
  exit 1
fi
print_resp "$resp"

# 2) Read status enum from OpenAPI (no auth)
echo "== Read status enum from OpenAPI =="
STATUSES="$(
  curl -s "$BASE/openapi.json" | python - <<'PY'
import json, sys

o = json.load(sys.stdin)
schemas = o.get("components", {}).get("schemas", {})

def find_enum(obj):
    if isinstance(obj, dict):
        if "enum" in obj and isinstance(obj["enum"], list):
            return obj["enum"]
        for v in obj.values():
            r = find_enum(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_enum(v)
            if r:
                return r
    return None

# Prova a trovare enum in CampaignStatusTransition.status
cst = schemas.get("CampaignStatusTransition", {})
status_enum = find_enum(cst.get("properties", {}).get("status", {}))

if not status_enum:
    # fallback: prova a trovare un enum "CampaignStatus" se esiste
    cs = schemas.get("CampaignStatus", {})
    status_enum = find_enum(cs)

if not status_enum:
    print("")
else:
    print(" ".join(status_enum))
PY
)"

if [[ -z "$STATUSES" ]]; then
  echo "Non riesco a estrarre gli enum stati da OpenAPI."
  echo "Apri $BASE/openapi.json e cerca CampaignStatusTransition / CampaignStatus."
  exit 1
fi

echo "Allowed statuses: $STATUSES"
echo

# helper: pick a status different from current
pick_next() {
  local current="$1"
  for s in $STATUSES; do
    if [[ "$s" != "$current" ]]; then
      echo "$s"
      return 0
    fi
  done
  echo "$current"
}

# 3) Create campaign
echo "== Create campaign =="
create_body='{
  "name": "Smoke Campaign 001",
  "description": "Sanity check",
  "language": "it",
  "intro_script": "Ciao, sono l assistente di test.",
  "question_1_text": "Come stai?",
  "question_1_type": "free_text",
  "question_2_text": "Da 1 a 5 quanto sei soddisfatto?",
  "question_2_type": "scale",
  "question_3_text": "Vuoi essere ricontattato?",
  "question_3_type": "free_text",
  "max_attempts": 2,
  "retry_interval_minutes": 60,
  "allowed_call_start_local": "09:00",
  "allowed_call_end_local": "18:00",
  "completion_message": "Grazie per il tempo dedicato."
}'

resp="$(curl_json POST "/api/campaigns" "$create_body")"
print_resp "$resp"

BODY="$(printf "%s" "$resp" | sed '$d')"
CID="$(printf "%s" "$BODY" | python - <<'PY'
import sys, json
o=json.load(sys.stdin)
print(o.get("id",""))
PY
)"
[[ -n "$CID" ]] || fail "Create OK ma non trovo 'id' nel response. Stampa sopra e verifica schema response."

echo "CID=$CID"
echo

# 4) Read current campaign (to know current status)
echo "== Get campaign =="
resp="$(curl_json GET "/api/campaigns/$CID")"
print_resp "$resp"
current_status="$(
  printf "%s" "$(printf "%s" "$resp" | sed '$d')" | python - <<'PY'
import sys, json
o=json.load(sys.stdin)
print(o.get("status",""))
PY
)"
echo "Current status: $current_status"
echo

# 5) Transition 1: current -> next different
echo "== Status transition #1 =="
next1="$(pick_next "$current_status")"
echo "Try: $current_status -> $next1"
resp="$(curl_json POST "/api/campaigns/$CID/status" "{\"status\":\"$next1\"}")"
print_resp "$resp"

# 6) Transition 2: try another different from next1
echo "== Status transition #2 =="
next2="$(pick_next "$next1")"
echo "Try: $next1 -> $next2"
resp="$(curl_json POST "/api/campaigns/$CID/status" "{\"status\":\"$next2\"}")"
print_resp "$resp"

# 7) Invalid transition check (try to go back to current_status)
echo "== Invalid transition check (expected 4xx) =="
echo "Try: $next2 -> $current_status (può essere invalida)"
resp="$(curl_json POST "/api/campaigns/$CID/status" "{\"status\":\"$current_status\"}" || true)"
print_resp "$resp"

echo "DONE."

