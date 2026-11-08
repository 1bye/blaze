#!/usr/bin/env python3
"""Run the fork archive's real Rake acceptance; JSON fields rake_root, cli, archive."""
from pathlib import Path
import json, subprocess, sys
v=json.loads(Path(sys.argv[1]).read_text())
if set(v)!={"rake_root","cli","archive"}:raise SystemExit("expected rake_root, cli, archive")
subprocess.run(["python3",str(Path(v["rake_root"])/"scripts/test-blaze-live.py"),json.dumps(v)],check=True)
