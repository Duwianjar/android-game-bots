#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec "$(command -v python3)" -u magic_gems_guardian.py "$@"
