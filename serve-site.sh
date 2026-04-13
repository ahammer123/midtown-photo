#!/usr/bin/env bash
# Local preview for any Mac — static site (no install beyond Python 3).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
PORT="${PORT:-9000}"
echo ""
echo "  Equipment list:  http://127.0.0.1:${PORT}/"
echo "  Editor:          http://127.0.0.1:${PORT}/admin.html"
echo ""
echo "  Press Ctrl+C to stop."
echo ""
exec python3 -m http.server "$PORT"
