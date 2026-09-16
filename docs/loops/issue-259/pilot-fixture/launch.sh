#!/bin/sh
# A synthetic startup profile is sourced by the launcher before the repo script.
. ./shell-profile.sh
exec "$PYTHON" pipeline.py input.json "$1"
