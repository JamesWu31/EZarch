#!/bin/sh
set -eu
if [ "$(uname -s)" != "Darwin" ]; then
  echo "EZarch releases support macOS and Windows only." >&2
  exit 2
fi
EZARCH_SKILL_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if command -v uv >/dev/null 2>&1; then
  EZARCH_UV=$(command -v uv)
else
  EZARCH_TOOL_DIR="$EZARCH_SKILL_ROOT/.ezarch/tools"
  mkdir -p "$EZARCH_TOOL_DIR"
  curl --fail --location --proto '=https' --tlsv1.2 https://astral.sh/uv/0.11.26/install.sh -o "$EZARCH_TOOL_DIR/install-uv.sh"
  UV_INSTALL_DIR="$EZARCH_TOOL_DIR" UV_NO_MODIFY_PATH=1 sh "$EZARCH_TOOL_DIR/install-uv.sh"
  EZARCH_UV="$EZARCH_TOOL_DIR/uv"
fi
exec "$EZARCH_UV" run --no-project --python 3.12 python "$EZARCH_SKILL_ROOT/scripts/bootstrap.py" "$@"
