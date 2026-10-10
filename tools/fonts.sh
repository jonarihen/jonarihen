#!/usr/bin/env bash
# Fetch the aaris.tech fonts (OFL) and pin the variable Archivo to the instances
# build.py expects. Output: tools/fonts/ (git-ignored).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts && cd fonts
B=https://cdn.jsdelivr.net/gh/google/fonts@main/ofl
curl -sfLo MonoMedium.ttf   $B/ibmplexmono/IBMPlexMono-Medium.ttf
curl -sfLo MonoSemiBold.ttf $B/ibmplexmono/IBMPlexMono-SemiBold.ttf
curl -sfLo Archivo.ttf      "$B/archivo/Archivo%5Bwdth,wght%5D.ttf"
python3 - <<'PY'
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
for name, loc in {"ArchivoDisplay": {"wdth": 125, "wght": 900}, "ArchivoRegular": {"wdth": 100, "wght": 400},
                  "ArchivoSemi": {"wdth": 100, "wght": 600}, "ArchivoBold": {"wdth": 100, "wght": 700}}.items():
    instancer.instantiateVariableFont(TTFont("Archivo.ttf"), loc).save(f"{name}.ttf")
PY
rm Archivo.ttf
