#!/usr/bin/env bash
# Filter four recreation renders and build the comparison sheets. Run from anywhere.
# KILN is a kiln checkout (for tools/bl and the reference images).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
KILN="${KILN:-$HOME/Work/3dmodels}"
rec="$here/../recreations"
font="$(fc-match -f '%{file}' sans)"
declare -A SRC=( [1]=final.png [2]=final.png [7]=final.png [9]=final_raw.png )
# 600 px crops per scene: "foliage rock" as WxH+X+Y in render pixels
declare -A CROPS=( [1]="600x400+680+60 600x400+640+319" [2]="600x400+0+319 600x400+340+150"
                   [7]="600x400+0+300 600x400+500+0" [9]="600x400+0+0 600x400+340+319" )
for n in 1 2 7 9; do
  out="$here/out/scene$n"; mkdir -p "$out"
  ( cd "$KILN" && tools/bl "$here/kuwahara.py" "$rec/scene$n/out/${SRC[$n]}" "$out" "$here/variants.json" ${DEVICE:-CPU} ) | grep TIME | tee "$out/times.txt"
  if [ "$n" = 7 ]; then
    ( cd "$KILN" && tools/bl "$here/kuwahara.py" "$rec/scene$n/out/${SRC[$n]}" "$out" "$here/probe.json" ${DEVICE:-CPU} ) | grep TIME | tee -a "$out/times.txt"
  fi
  magick "$rec/scene$n/out/${SRC[$n]}" "$out/render.png"
  size=$(magick identify -format '%wx%h' "$out/render.png")
  magick "$KILN/docs/style/refs/owner/scene-$n.png" -resize "$size!" "$out/reference.png"
  names="reference render aniso_subtle aniso_mid aniso_strong classic_mid mid_preblur mid_posterize mid_canvas mid_edges"
  args=(); for v in $names; do args+=( -label "$v" "$out/$v.png" ); done
  magick montage "${args[@]}" -font "$font" -pointsize 28 -tile 2x -geometry +6+6 -background '#202028' -fill white "$here/out/sheet_scene$n.png"
  i=0
  for c in ${CROPS[$n]}; do
    i=$((i+1)); kind=$([ $i = 1 ] && echo foliage || echo rock)
    args=(); for v in $names; do args+=( -label "$v" \( "$out/$v.png" -crop "$c" +repage \) ); done
    magick montage "${args[@]}" -font "$font" -pointsize 20 -tile 2x -geometry +4+4 -background '#202028' -fill white "$here/out/crops_scene${n}_$kind.png"
  done
done
c="600x400+500+250"
args=(); for v in render aniso_mid p_ecc0 p_ecc2 p_sharp0 p_unif0 p_unif16 p_classic_hp p_2pass p_size30; do args+=( -label "$v" \( "$here/out/scene7/$v.png" -crop "$c" +repage \) ); done
magick montage "${args[@]}" -font "$font" -pointsize 20 -tile 2x -geometry +4+4 -background '#202028' -fill white "$here/out/probe_scene7.png"
