#!/bin/bash
# instalar.sh — onboarding del guardia de memoria (idempotente).
# El guard NO viaja con el clone (core.hooksPath vive en .git/config):
# correr esto una vez por clone, tras crear .venv (ver README/AGENTS.md).
set -e
cd "$(dirname "$0")/../.."

git config core.hooksPath scripts/hooks
chmod +x scripts/hooks/pre-commit scripts/mem 2>/dev/null || true

if [ ! -x .venv/bin/python ]; then
  echo "instalar: aviso — .venv ausente; crea el venv e instala an-kla-memory@v0.1.0-beta.19 (ADR-007)"
else
  echo "instalar: .venv detectado"
fi
echo "instalar: hooks activos (core.hooksPath=scripts/hooks)"
