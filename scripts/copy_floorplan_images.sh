#!/bin/sh
# One-shot script: copies floor plan images from HA image_upload storage
# into www/images/ so they can be served at /local/images/ and git-tracked.
# Run once on the HA device, then delete this script.

set -e

SRC_LIGHT="/config/image/5f4a6ab8a9c1d92fe82541508c3ebd2c/original"
SRC_DARK="/config/image/b3ed721bbc86aafdb9ff0ab2a48467d9/original"
DEST="/config/www/images"

mkdir -p "$DEST"

cp "$SRC_LIGHT" "$DEST/floorplan-light.png"
cp "$SRC_DARK"  "$DEST/floorplan-dark.png"

echo "Done. Images copied to $DEST/"
echo "  floorplan-light.png ($(wc -c < "$DEST/floorplan-light.png") bytes)"
echo "  floorplan-dark.png  ($(wc -c < "$DEST/floorplan-dark.png") bytes)"
echo ""
echo "Next: the auto-push script will commit these to git."
echo "You can delete this script afterwards."
