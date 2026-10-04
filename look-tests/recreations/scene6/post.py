#!/usr/bin/env python3
"""post.py raw.png out.png : sun glow, lens-flare streak and ghosts, slight softening (ImageMagick)."""
import subprocess, sys
IN, OUT = sys.argv[1:3]
W, H = map(int, subprocess.check_output(["magick", "identify", "-format", "%w %h", IN]).split()); k = W / 500
G = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
def layer(shapes, blur, mul):
    a = ["(", "-size", f"{W}x{H}", "xc:black"]
    for col, cx, cy, rx, ry, rot in shapes:
        a += ["-fill", col, "-draw", f"translate {cx*k:.1f},{cy*k:.1f} rotate {rot} ellipse 0,0 {rx*k:.1f},{ry*k:.1f} 0,360"]
    return a + ["-blur", f"0x{blur*k:.1f}", "-evaluate", "multiply", str(mul * G), ")", "-compose", "screen", "-composite"]
cmd = ["magick", IN]
cmd += layer([("rgb(255,232,185)", 168, 4, 95, 60, 0)], 55, 0.6)
cmd += layer([("rgb(255,240,205)", 325, 8, 40, 40, 0)], 35, 0.5)
cmd += layer([("rgb(255,225,170)", 168, 45, 7, 75, 12), ("rgb(255,170,90)", 157, 88, 6, 16, 12), ("rgb(200,150,255)", 161, 62, 5, 12, 12)], 6, 0.8)
cmd += layer([("rgb(255,235,200)", 325, 40, 5, 50, 0), ("rgb(90,230,120)", 291, 122, 4, 4, 0)], 4, 0.45)
cmd += ["-blur", f"0x{0.35*k:.2f}", OUT]
subprocess.check_call(cmd)
