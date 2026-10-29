#!/bin/sh
# Compatibility entry point; keep the implementation in tools/.
exec bash "$(dirname "$0")/../build_deps.sh" "$@"
