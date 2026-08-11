#!/usr/bin/env bash
set -euo pipefail

# The embedding listener is a worker-private service. A public Railway route or
# provider credential in the API process breaks the capability boundary.
rg -q '"publicNetworking"[[:space:]]*:[[:space:]]*false' railway.json
rg -q '"privateNetworking"[[:space:]]*:[[:space:]]*true' railway.json
if rg -n '^[[:space:]]*(OPENROUTER_API_KEY|OPENAI_API_KEY|DATABASE_URL|SUPABASE_SECRET_KEY)[[:space:]]*:' apps/api/src/api; then
  echo "API-side provider or service credential found" >&2
  exit 1
fi
