#!/bin/sh
# Rebuild [M] with the item markers of regionmarks.tex and the display and step markers of
# regionmarks-steps.tex, which ../steps/marks.py writes into a scratch copy of the source; check
# that its layout is the committed main.pdf's.
#   sh build-steps.sh <manuscript dir> <build dir> <committed main.pdf> <seg json>
# Needs what build.sh needs.
set -eu
src=$1 build=$2 pdf=$3 seg=$4
here=$(cd "$(dirname "$0")" && pwd)
rm -rf "$build"
mkdir -p "$build"
cp -r "$src"/main.tex "$src"/macros.tex "$src"/references.bib "$src"/part1 "$src"/part2 "$build"/
cp "$here/regionmarks.tex" "$here/regionmarks-steps.tex" "$build"/
python3 -I "$here/../steps/marks.py" "$seg" "$build"
python3 -I "$here/ecmap.py" "$build/ecfake.map"
python3 -I -c '
import sys
p = sys.argv[1] + "/main.tex"
s = open(p).read()
k = "\\begin{document}"
if "\\input{regionmarks}" not in s:
    s = s.replace(k, "\\input{regionmarks}\n\\input{regionmarks-steps}\n" + k, 1)
open(p, "w").write(s)' "$build"
cd "$build"
for i in 1 2 3; do
  pdflatex -interaction=nonstopmode '\pdfmapfile{+ecfake.map}\input{main}' > "run$i.log" 2>&1 || true
  [ $i = 1 ] && { bibtex main > bibtex.log 2>&1 || true; }
done
cd - > /dev/null
python3 -I "$here/layoutcheck.py" "$pdf" "$build/main.pdf" "$build/layoutcheck.json"
