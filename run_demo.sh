#!/usr/bin/env bash
# Convenience wrapper at repo root.
exec "$(cd "$(dirname "$0")" && pwd)/scripts/run_demo.sh" "$@"
