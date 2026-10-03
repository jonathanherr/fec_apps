#!/bin/sh
# Start the FEC x Jev explorer. Serves http://127.0.0.1:8741
# Usage: ./start.sh  (override port: PORT=9000 ./start.sh)
cd "$(dirname "$0")" || exit 1
[ -n "$PORT" ] && export FECJEV_PORT="$PORT"
exec python3 server.py
