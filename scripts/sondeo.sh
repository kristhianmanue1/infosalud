#!/bin/bash
# Sondeo mensual de vigencias (ADR-008, decisión 8): verificación
# read-only de todas las fuentes con URL registrada. Sin CI: se
# programa localmente con launchd (ver docs/sondeo-launchd.md).
set -u
cd "$(dirname "$0")/.." || exit 1
LOG="data/sondeo.log"
echo "== sondeo $(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$LOG"
ids=$(python3 -m infosalud fuente-lista --json \
  | python3 -c "import json,sys; f=json.load(sys.stdin)['fuentes']; \
print(' '.join(x['id'] for x in f))")
for id in $ids; do
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $id" >> "$LOG"
  if ! python3 -m infosalud vigencia-verificar "$id" >> "$LOG" 2>&1; then
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $id: fallo" >> "$LOG"
  fi
done
echo "== fin $(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$LOG"
