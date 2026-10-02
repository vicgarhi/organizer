#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Requires the build host to match Python 3.12 and the target Linux architecture.
.venv/bin/python -m pip wheel --disable-pip-version-check -r requirements.lock --wheel-dir deploy/wheels
.venv/bin/python - <<'PY'
from pathlib import Path
import hashlib
root=Path('deploy/wheels')
(root/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(root.glob('*.whl'))))
PY
