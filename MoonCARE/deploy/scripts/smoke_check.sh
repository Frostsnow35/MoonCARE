#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-${1:-}}"
LOGIN_EMAIL="${LOGIN_EMAIL:-}"
LOGIN_PASSWORD="${LOGIN_PASSWORD:-}"
CURL_INSECURE="${CURL_INSECURE:-false}"

if [[ -z "$BASE_URL" ]]; then
  echo "Usage: BASE_URL=http://SERVER_IP bash deploy/scripts/smoke_check.sh" >&2
  echo "Optional: LOGIN_EMAIL=... LOGIN_PASSWORD=... CURL_INSECURE=true" >&2
  exit 1
fi

BASE_URL="${BASE_URL%/}"
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "python3 or python is required for smoke_check.sh" >&2
    exit 1
  fi
fi

declare -a CURL_FLAGS=(-sS)
if [[ "$CURL_INSECURE" == "true" ]]; then
  CURL_FLAGS+=(-k)
fi

request_status() {
  local path="$1"
  local method="${2:-GET}"
  local body_file
  body_file="$(mktemp)"
  local status
  status="$(curl "${CURL_FLAGS[@]}" -o "$body_file" -w "%{http_code}" -X "$method" "$BASE_URL$path")"
  echo "$status|$body_file"
}

assert_status() {
  local path="$1"
  local expected="$2"
  local method="${3:-GET}"
  local result
  result="$(request_status "$path" "$method")"
  local status="${result%%|*}"
  local body_file="${result#*|}"
  if [[ "$status" != "$expected" ]]; then
    echo "Unexpected status for $path: got $status expected $expected" >&2
    cat "$body_file" >&2
    rm -f "$body_file"
    exit 1
  fi
  rm -f "$body_file"
  echo "OK $path -> $status"
}

assert_status "/healthz" "200"
assert_status "/docs" "404"
assert_status "/redoc" "404"
assert_status "/openapi.json" "404"
assert_status "/metrics" "404"

if [[ -n "$LOGIN_EMAIL" && -n "$LOGIN_PASSWORD" ]]; then
  login_payload="$(printf '{"email":"%s","password":"%s"}' "$LOGIN_EMAIL" "$LOGIN_PASSWORD")"
  login_body="$(mktemp)"
  login_status="$(curl "${CURL_FLAGS[@]}" -o "$login_body" -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -X POST \
    -d "$login_payload" \
    "$BASE_URL/api/v1/auth/login")"
  if [[ "$login_status" != "200" ]]; then
    echo "Login failed: HTTP $login_status" >&2
    cat "$login_body" >&2
    rm -f "$login_body"
    exit 1
  fi
  token="$("$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])' < "$login_body")"
  rm -f "$login_body"
  echo "OK /api/v1/auth/login -> 200"

  session_body="$(mktemp)"
  session_status="$(curl "${CURL_FLAGS[@]}" -o "$session_body" -w "%{http_code}" \
    -H "Authorization: Bearer $token" \
    -X POST \
    "$BASE_URL/api/v1/chat/session")"
  if [[ "$session_status" != "200" ]]; then
    echo "Create session failed: HTTP $session_status" >&2
    cat "$session_body" >&2
    rm -f "$session_body"
    exit 1
  fi
  session_id="$("$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["session_id"])' < "$session_body")"
  rm -f "$session_body"
  echo "OK /api/v1/chat/session -> 200 session_id=$session_id"
else
  echo "Skipped auth smoke checks because LOGIN_EMAIL / LOGIN_PASSWORD were not provided."
fi
