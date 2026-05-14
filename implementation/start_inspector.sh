#!/bin/bash
# Run MCP Inspector against the SQLite Lab server
# Usage: bash start_inspector.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python)"

mkdir -p "$SCRIPT_DIR/.npm-cache"
NPM_CONFIG_CACHE="$SCRIPT_DIR/.npm-cache" npx -y @modelcontextprotocol/inspector \
  "$PYTHON" "$SCRIPT_DIR/mcp_server.py"
