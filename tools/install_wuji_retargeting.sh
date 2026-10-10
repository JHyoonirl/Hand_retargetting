#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if [[ -n "${PYTHON_BIN:-}" ]]; then
  python_bin=$PYTHON_BIN
elif [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
  python_bin="${VIRTUAL_ENV}/bin/python"
else
  python_bin=python3
fi

command -v "$python_bin" >/dev/null 2>&1 || {
  echo "Python interpreter not found: $python_bin" >&2
  exit 2
}
"$python_bin" -m pip --version >/dev/null 2>&1 || {
  echo "pip is required for wuji-retargeting; install python3-pip or activate .venv" >&2
  exit 2
}

pip_flags=()
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  # Ubuntu's system Python is externally managed; Docker/system installs need
  # this explicit opt-in. A project .venv never takes this branch.
  pip_flags+=(--break-system-packages)
fi

"$python_bin" -m pip install "${pip_flags[@]}" -r \
  "$root/vendor/wuji-retargeting/requirements.runtime.txt"
"$python_bin" -m pip install "${pip_flags[@]}" --no-deps -e \
  "$root/vendor/wuji-retargeting"

WUJI_REPO_ROOT="$root" "$python_bin" - <<'PY'
import os
from wuji_retargeting import Retargeter
from pathlib import Path

root = Path(os.environ["WUJI_REPO_ROOT"])
config = root / "vendor/wuji-retargeting/config/retarget_manus_right.yaml"
retargeter = Retargeter.from_yaml(str(config), "right")
assert retargeter.num_joints == 20
print(f"wuji-retargeting ready ({retargeter.num_joints} joints): {config}")
PY
