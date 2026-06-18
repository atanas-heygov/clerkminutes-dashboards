#!/bin/bash
#
# Double-click this file to start the Custom tier tracker preview.
# It launches two local servers and opens the page in your browser.
# Leave the Terminal window that opens running. Close it (or press Ctrl+C) to stop.
#
export PATH="/usr/local/bin:$PATH"
ROOT="/Users/User/Documents/HeyGovApp"

echo "==============================================="
echo "  Starting Custom tier tracker preview…"
echo "==============================================="

# Stop any old copies so ports 4500 / 8080 are free
pkill -f "dev-proposals-proxy.mjs" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 1

# 1) Data preview server (port 4500)
node "$ROOT/dev-proposals-proxy.mjs" &
PROXY_PID=$!

# 2) Dashboard (port 8080)
cd "$ROOT/dashboard" || exit 1
npm run dev &
DASH_PID=$!

# Stop both servers when this window is closed / Ctrl+C
trap "echo; echo 'Stopping…'; kill $PROXY_PID $DASH_PID 2>/dev/null; exit 0" INT TERM EXIT

# Wait for the dashboard to be ready, then open the browser
echo "Waiting for the dashboard to start…"
for i in $(seq 1 30); do
	if curl -s -o /dev/null http://localhost:8080/ ; then break; fi
	sleep 1
done

open "http://localhost:8080/heygov-admin/custom-tier-tracker"

echo ""
echo "==============================================="
echo "  Ready!  Page: http://localhost:8080/heygov-admin/custom-tier-tracker"
echo "  Keep THIS window open while you use it."
echo "  To stop: close this window or press Ctrl+C."
echo "==============================================="

wait
