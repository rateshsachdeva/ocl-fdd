from __future__ import annotations

import subprocess
import sys

raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", *sys.argv[1:]]))
