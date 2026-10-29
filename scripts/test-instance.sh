#!/bin/sh
# An isolated instance for automated tests: its own port, inbox and runs dir, so a shared server is never reset mid-test.
# The LLM credentials come from the environment (see .env.example); nothing is read from a fixed path.
#   scripts/test-instance.sh smoke [port]   start on PORT (default 8020), run scripts/smoke_e2e.py against it, stop
#   scripts/test-instance.sh start [port] / stop [port]
cd "$(dirname "$0")/.." || exit 1
CMD="${1:-smoke}"; PORT="${2:-8020}"
BASE="${TMPDIR:-/tmp}/succesiune-test-$PORT"
PY="${PYTHON:-.venv/bin/python}"
stop() {
  for f in "$BASE"/*.pid; do [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null; done
  rm -f "$BASE"/*.pid
}
start() {
  stop; rm -rf "$BASE"; mkdir -p "$BASE/inbox" "$BASE/runs"
  export DEMO_MODE=1 RUNS_DIR="$BASE/runs" AUTOPILOT_INBOX="$BASE/inbox" RUN_ID="test-$PORT-$(date +%H%M%S)"
  setsid nohup "$PY" -m uvicorn agent.api:app --host 127.0.0.1 --port "$PORT" > "$BASE/api.log" 2>&1 < /dev/null &
  echo $! > "$BASE/api.pid"
  sleep 3
  setsid nohup "$PY" -u scripts/autopilot.py --watch --api "http://127.0.0.1:$PORT" > "$BASE/autopilot.log" 2>&1 < /dev/null &
  echo $! > "$BASE/autopilot.pid"
  sleep 2
  curl -s -m 5 "http://127.0.0.1:$PORT/health" >/dev/null || { echo "instanța de test nu răspunde (vezi $BASE/api.log)"; return 1; }
  echo "instanță de test pe :$PORT · inbox $BASE/inbox · runs $BASE/runs"
}
case "$CMD" in
  start) start ;;
  stop) stop; echo "oprită :$PORT" ;;
  smoke)
    start || exit 2
    AUTOPILOT_INBOX="$BASE/inbox" RUNS_DIR="$BASE/runs" "$PY" scripts/smoke_e2e.py --api "http://127.0.0.1:$PORT"
    rc=$?; stop; exit $rc ;;
  *) echo "folosire: $0 smoke|start|stop [port]"; exit 64 ;;
esac
