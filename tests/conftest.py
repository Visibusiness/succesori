"""Tests never write into the real runs/: agent.trace reads RUNS_DIR at import, so it is set before any test module
imports agent.api (otherwise every pytest run made a new runs/<stamp> and moved runs/latest away from the live server)."""
import os
import tempfile

os.environ["RUNS_DIR"] = tempfile.mkdtemp(prefix="runs-test-")
os.environ.pop("RUN_ID", None)
# 076: a quarantined document is kept as evidence; tests keep it out of the real registries/inbox/quarantine/
os.environ.setdefault("GUARD_QUARANTINE_DIR", tempfile.mkdtemp(prefix="quarantine-test-"))
# 084: the unit tests start from an empty bank (POST /demo/reset = only Maria in core); tests/test_portfolio.py asks for
# the portfolio explicitly. The SQLite state goes under the temp RUNS_DIR (agent/store.py default_path).
os.environ.setdefault("MVP_PORTFOLIO", "0")
