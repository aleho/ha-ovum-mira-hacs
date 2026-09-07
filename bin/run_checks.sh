#!/usr/bin/env bash
set -euox pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
PIP_BIN="${PIP_BIN:-.venv/bin/pip}"

cd "$ROOT_DIR"

echo "==> Installing project dependencies"
"$PIP_BIN" install \
    --root-user-action=ignore \
    -e .

if ! "$PYTHON_BIN" -m ruff --version >/dev/null 2>&1; then
    echo "==> Installing Ruff"
    "$PIP_BIN" install \
        --root-user-action=ignore \
        "ruff>=0.9"
fi

echo "==> Checking formatting"
"$PYTHON_BIN" -m ruff format --check .

echo "==> Running Ruff"
"$PYTHON_BIN" -m ruff check .

echo "==> All checks passed"
