#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"   # project root

# Optional: update timestamp
echo "[push.sh] Sync started at $(date)"

git add -A
git commit -m "Auto journal sync $(date '+%Y-%m-%d %H:%M:%S')" || true
git push origin main || git push origin master || true
