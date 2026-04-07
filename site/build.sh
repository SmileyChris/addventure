#!/bin/sh
set -e
# Build docs, example PDF, then overlay the custom landing page
cd "$(dirname "$0")/.."
zensical build -c "$@"
uv run addventure build games/example -o site/assets/the-facility.pdf
uv run addventure build games/example/the-outpost -o site/assets/the-facility_epilogue.pdf
cp site/index.html site/build/index.html
cp -r site/assets site/build/
