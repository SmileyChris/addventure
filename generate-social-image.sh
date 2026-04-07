#!/usr/bin/env bash
# Generate the GitHub social preview image (1280x640 JPG)
# Requires: ImageMagick 7+, Montserrat Black font, Alegreya Italic font
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$SCRIPT_DIR/repository-open-graph.jpg}"
LOGO="$SCRIPT_DIR/site/assets/images/logo.png"

# Fonts
MONTSERRAT_BLACK="/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-Black.otf"
ALEGREYA_ITALIC=""

# Try common Alegreya locations, fall back to download
for f in \
  /usr/share/fonts/*/Alegreya-Italic*.ttf \
  /usr/share/fonts/*/Alegreya-Italic*.otf \
  "$HOME/.local/share/fonts/Alegreya-Italic.ttf"; do
  [ -f "$f" ] && ALEGREYA_ITALIC="$f" && break
done
if [ -z "$ALEGREYA_ITALIC" ]; then
  ALEGREYA_ITALIC="/tmp/Alegreya-Italic.ttf"
  if [ ! -f "$ALEGREYA_ITALIC" ]; then
    echo "Downloading Alegreya Italic..."
    curl -sL "https://github.com/google/fonts/raw/main/ofl/alegreya/Alegreya-Italic%5Bwght%5D.ttf" \
      -o "$ALEGREYA_ITALIC"
  fi
fi

GRID_TILE="$(mktemp /tmp/grid-tile-XXXX.png)"
trap 'rm -f "$GRID_TILE"' EXIT

# Grid tile: subtle gold lines
magick -size 40x40 xc:none \
  -stroke 'rgba(201,168,76,0.04)' -strokewidth 1 \
  -draw "line 0,0 39,0" -draw "line 0,0 0,39" \
  "$GRID_TILE"

# Compose final image
magick -size 1280x640 xc:'#0b0a09' \
  \( -size 800x800 radial-gradient:'rgba(201,168,76,0.11)-none' \) \
  -gravity Center -geometry +0-180 -composite \
  \( -size 1280x640 xc:none -tile "$GRID_TILE" -draw "rectangle 0,0 1280,640" \
     \( -size 1400x900 radial-gradient:white-black -resize '1280x640!' -level '20%,100%' \) \
     -compose DstIn -composite \) \
  -compose Screen -composite \
  \( "$LOGO" -resize 330x330 \) \
  -gravity Center -compose Over -geometry +0-100 -composite \
  -fill '#f5e6a8' -font "$MONTSERRAT_BLACK" \
  -pointsize 72 -kerning 6 -gravity Center -annotate +0+105 "ADDVENTURE" \
  -fill '#9a9088' -font "$ALEGREYA_ITALIC" \
  -pointsize 30 -kerning 0 -gravity Center -annotate +0+195 \
  "Write interactive fiction played with pencil, paper, and addition." \
  "$OUT"

echo "Generated: $OUT"
