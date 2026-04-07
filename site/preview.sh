#!/bin/sh
# Live-reload dev server for the full site
# Watches docs/ (rebuilds via zensical) and site/index.html + assets/ (fast overlay copy)
cd "$(dirname "$0")/.."
[ -d site/build ] || site/build.sh
exec uv run python3 site/preview.py "$@"
