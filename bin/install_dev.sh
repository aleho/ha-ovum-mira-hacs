#!/usr/bin/env bash
set -e

python3 -m venv .venv
.venv/bin/pip install --upgrade -e './[dev]'
.venv/bin/pip install --upgrade -e ../ovum-mira-modbus
