#!/bin/sh
# Rebuild [M] (manuscript/ of yang-mills-informalization) with the position markers of
# regionmarks.tex, check that its layout is the committed main.pdf's, and place the regions.
#   sh build.sh <manuscript dir> <build dir> <committed main.pdf> <items json> <out regions json> <source commit>
# Needs pdflatex and bibtex (TeX Live, with the EC metrics and Latin Modern Type 1 fonts), poppler
# and Python 3.  ecmap.py gives the EC fonts Type 1 outlines (see there).
set -eu
src=$1 build=$2 pdf=$3 items=$4 out=$5 commit=$6
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$build"
cp -r "$src"/main.tex "$src"/macros.tex "$src"/references.bib "$src"/part1 "$src"/part2 "$build"/
cp "$here/regionmarks.tex" "$build"/
python3 -I "$here/ecmap.py" "$build/ecfake.map"
python3 -I -c '
import sys
p = sys.argv[1] + "/main.tex"
s = open(p).read()
k = "\\begin{document}"
if "\\input{regionmarks}" not in s:
    s = s.replace(k, "\\input{regionmarks}\n" + k, 1)
open(p, "w").write(s)' "$build"
cd "$build"
for i in 1 2 3; do
  pdflatex -interaction=nonstopmode '\pdfmapfile{+ecfake.map}\input{main}' > "run$i.log" 2>&1 || true
  [ $i = 1 ] && { bibtex main > bibtex.log 2>&1 || true; }
done
cd - > /dev/null
python3 -I "$here/layoutcheck.py" "$pdf" "$build/main.pdf" "$build/layoutcheck.json"
python3 -I "$here/regions.py" "$build" "$pdf" "$items" "$out" "$commit"
