#!/usr/bin/env bash
# Separate, explicit Hermes package installer; never invokes the Codex installer.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT_DIR/scripts/project-python" "$ROOT_DIR/scripts/hermes-package.py" "$@"
