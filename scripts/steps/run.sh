#!/bin/sh
# Displays outside proofs, proof steps and their regions on the committed main.pdf.
#   sh run.sh <manuscript dir> <committed main.pdf> <work dir> <source commit>
# The sentence groups of the paragraphs over finalize.py's LONG printed lines
# (data/manuscript-step-splits.json) were made once, by reading; this script reuses them.
set -eu
src=$1 pdf=$2 work=$3 commit=$4
here=$(cd "$(dirname "$0")" && pwd)
data=$here/../../data
mkdir -p "$work"
python3 -I "$here/segment.py" "$src" "$data/items.json" "$commit" "$work/seg.json"
sh "$here/../regions/build-steps.sh" "$src" "$work/build" "$pdf" "$work/seg.json"
python3 -I "$here/../regions/steps_regions.py" lines "$work/build" "$pdf" "$work/seg.json" "$work/lines.json"
python3 -I "$here/finalize.py" "$work/seg.json" "$work/lines.json" - "$work/displays.json" "$work/steps.json" "$data/manuscript-step-splits.json"
python3 -I "$here/../regions/steps_regions.py" regions "$work/build" "$pdf" "$work/steps.json" "$work/displays.json" \
  "$data/regions.json" "$data/items.json" "$work/regions.json" "$commit"
# titles and pages from the regions; the regions do not depend on them
python3 -I "$here/finalize.py" "$work/seg.json" "$work/lines.json" "$work/regions.json" \
  "$data/manuscript-displays.json" "$data/manuscript-steps.json" "$data/manuscript-step-splits.json"
python3 -I "$here/../regions/steps_regions.py" regions "$work/build" "$pdf" "$data/manuscript-steps.json" \
  "$data/manuscript-displays.json" "$data/regions.json" "$data/items.json" "$data/manuscript-regions-steps.json" "$commit"
