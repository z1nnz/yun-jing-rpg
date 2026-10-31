#!/bin/sh
# Review renders for the C day 1-2 models (Eli-0731). Run from the repo root:
#   BLENDER=<blender.exe> [WR=<path to qingxi-water-report-c exports>] sh art/source/qingxi-day12-c/render_reviews.sh
# WR points at the water-report corner exports (PR #55) for the side-by-side; skipped when missing.
set -e
B="${BLENDER:?set BLENDER to blender.exe}";RIG=art/source/qingxi-day12-c/render_day12.py
E=art/exports/qingxi-day12-c;P=art/previews/qingxi-day12-c
r(){ "$B" -b --factory-startup -P "$RIG" -- "$@" >/dev/null 2>&1 || echo "render failed: $*"; }
# 1. four views with the 1.75 m figure + wireframe (lamps unlit in the turnaround, as in the brief)
for k in RK03 G01 TY04 TY08 TY09; do
  g=""; case $k in G01|TY04) g="--glow 0";; esac
  r --glb $E/$k.glb --out $P/$k --tag $k --views front,side,back,threequarter --wire $g
done
# 2. lamp states: G01 unlit / lit by day and night; TY04 five brightness levels by day and night
for L in day night; do
  r --glb $E/G01.glb --out $P/G01/states --tag G01-$L-unlit --views threequarter --glow 0 --light $L --no-ruler
  r --glb $E/G01.glb --out $P/G01/states --tag G01-$L-lit --views threequarter --glow 1.2 --light $L --no-ruler
  i=0; for s in 0 0.35 0.9 1.7 2.8; do
    r --glb $E/TY04.glb --out $P/TY04/levels --tag TY04-$L-level$i --views front --glow $s --light $L --no-ruler --res 640x960; i=$((i+1))
  done
done
# 3. drying rack empty / full
r --glb $E/TY08.glb --out $P/TY08/states --tag TY08-empty --views threequarter --hide Herbs --no-ruler
r --glb $E/TY08.glb --out $P/TY08/states --tag TY08-full --views threequarter --no-ruler
# 4. 1.7 m eye height
r --glb $E/RK03.glb --out $P/eye --tag RK03-road-1p7m --views "" --cam=-2.2,-9.5,1.7,0,0,1.8,26 --ruler-x 3.6
r --glb $E/G01.glb,$E/G01.glb --at="-3.6,0,0;3.6,0,0" --out $P/eye --tag G01-gate-day-1p7m --views "" --cam=0,-9,1.7,0,0,1.3,30 --glow 0 --ruler-x 1.2
r --glb $E/G01.glb,$E/G01.glb --at="-3.6,0,0;3.6,0,0" --out $P/eye --tag G01-gate-night-1p7m --views "" --cam=0,-9,1.7,0,0,1.3,30 --glow 1.2 --light night --ruler-x 1.2
r --glb $E/TY04.glb,$E/TY08.glb,$E/TY09.glb --at="-5.2,12.0,0;5.4,4.0,90;5.0,11.5,180" --out $P/eye --tag yard-from-backdoor-1p7m --views "" --cam=2,0.5,1.7,3,9,0.8,18 --glow 0.35 --ruler-x 1.0
# 5. side by side with existing work
r --glb $E/G01.glb,$E/TY04.glb,art/exports/qingxi-detail-props-v2/qingxi-trail-lantern-v2.glb --at="-.9,0,0;.3,0,0;1.5,0,0" --out $P/compare --tag lanterns-G01-TY04-trail --views front,threequarter --glow 0
r --glb $E/RK03.glb,art/incoming/dondon/StarterHouse/v004/StarterHouse_v004.fbx --at="-4,0,0;4.6,0,0" --out $P/compare --tag RK03-vs-starterhouse --views front,threequarter
# WR must be a Windows-style path for Blender (E:/...); in Git Bash also set MSYS_NO_PATHCONV=1
if [ -n "$WR" ] && [ -f "$WR/c01-v002/C01_CouncilTable_v002.glb" ]; then
  r --glb $E/TY08.glb,$E/TY09.glb,$WR/c01-v002/C01_CouncilTable_v002.glb,$WR/v002/C02_v002.glb,$WR/v002/C04_v002.glb \
    --at="-2.2,0,0;0,0,0;1.9,0,0;3.4,0,0;4.4,0,0" --out $P/compare --tag yard-vs-water-corner --views front,threequarter
fi
echo REVIEWS_DONE
