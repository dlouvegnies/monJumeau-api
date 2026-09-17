#!/usr/bin/env bash
# ZEOPY API — la commande officielle des tests.
#
# Vide le bytecode avant de jouer : un __pycache__ périmé fait passer des
# tests sur une version antérieure du code. Constaté le 17/09 — deux mutations
# viraient au vert alors qu'elles auraient dû mordre, parce que pytest lisait
# du bytecode d'avant la mutation. Un contrôle qui dort ressemble à un
# contrôle qui passe.
#
# Usage, depuis la racine du dépôt :  bash tests/run.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
find . -name "__pycache__" -type d -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
exec python3 -m pytest tests/ -q -p no:cacheprovider "$@"
