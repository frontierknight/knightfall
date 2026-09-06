#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
exec python3 /knightfall/run.py "$@"
