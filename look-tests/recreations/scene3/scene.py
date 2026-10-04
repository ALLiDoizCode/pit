"""PROTOTYPE: recreation of owner reference scene 3 (inverted forest: hanging twisted trunks and cap platforms in dusk mist), without characters.
Usage: tools/bl scene.py out.png WIDTH SAMPLES   (SAMPLES=0 writes a vertex-splat layout preview .ppm instead of rendering)"""
import sys, math, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import kit
from kit import P, px_radius
from mathutils import Vector
OUT, WIDTH, SAMPLES = sys.argv[sys.argv.index("--") + 1:][:3]
kit.setup(500, 280, lens=40, pitch_deg=0)

# ---- materials -------------------------------------------------------------------------
bark = kit.uv_material("bark", ("#22171b", "#47322f", "#826656"), uscale=9, vscale=0.5, bump=1.0)
bark_far = kit.uv_material("bark_far", ("#3a2a30", "#5a4046", "#80605e"), uscale=4, vscale=0.4, bump=0.5)
nest = kit.uv_material("nest", ("#1d161b", "#40302e", "#70583f"), uscale=70, vscale=6, ribs=46, bands=11, bump=0.9, crease=0.65, glow=0.25)
cap_main = kit.uv_material("cap_main", ("#211b1f", "#342c2f", "#473d3b"), vcols=("#272b24", "#393f34", "#505642"), uscale=220, vscale=7, ribs=104, bands=6, crease=0.55, vmix=(0.25, 0.8))
cap_green = kit.uv_material("cap_green", ("#2c3a30", "#44574a", "#5f755c"), vcols=("#3b4a36", "#55684a", "#788a5e"), uscale=60, vscale=5, ribs=18, bands=5, crease=0.45, glow=0.15)
cap_teal = kit.uv_material("cap_teal", ("#22303a", "#33485a", "#4a6470"), vcols=("#2c4048", "#44606a", "#638088"), uscale=60, vscale=5, ribs=16, bands=5, crease=0.45, glow=0.15)
cap_brown = kit.uv_material("cap_brown", ("#3a2a2c", "#5a3c36", "#7a5040"), uscale=60, vscale=3, ribs=16, bands=3, crease=0.4)
bud = kit.uv_material("bud", ("#5e5560", "#857a84", "#a89aa0"), uscale=6, vscale=0.6, bump=0.4)
moss = kit.rock_material("moss", rock=("#231d1f", "#35302c", "#474236"), grass=("#2a3324", "#434e36"), grass_from=0.55)
moss_far = kit.rock_material("moss_far", rock=("#2a2a30", "#3a3c40", "#4a4e4a"), grass=("#30403a", "#4a5c4c"), grass_from=0.55)

def lift_main(a):      # the right-hand half of the big cap's rim stands higher, with a step where the figures stood
    c = math.cos(a); s = min(1.0, max(0.0, (c - 0.08) / 0.12)); return 0.85 * s * s * (3 - 2 * s) + 0.3 * max(c, 0)

# ---- the big near platform ---------------------------------------------------------------
kit.cap("main", P(150, 252, 16.5), P(221, 178, 17.2), 5.65, 4.6, cap_main, moss, normal=(0.0, 0.13, 1), ribs=104, rib_amp=0.016, shingles=6, shingle_amp=0.014,
        round_=1.9, ragged=0.1, lift=lift_main, seed=3, mound=0.055, dish=0.05, segs=624, rings=80)

# dark growth draped along the big cap's rim (taken from the cap's own rim points), taller on the raised right half
core_rim = kit.flat_material("core_rim", "#1c191a"); leaf_rim = kit.leaf_material("leaf_rim", "#211e1e", "#322f2b", "#434434", "#5c5e46", glow=0.05)
rnd = random.Random(4); rims, up = kit.LAST_RIM; inward = P(221, 178, 17.2)
for k in range(0, len(rims), 6):
    a = k / len(rims) * math.tau; hi = math.cos(a) > 0.15
    r = rnd.uniform(0.16, 0.3) if hi else rnd.uniform(0.1, 0.2)
    c = rims[k].lerp(inward, rnd.uniform(0.03, 0.12)) + up * r * 0.5
    kit.foliage("rimgrowth", c, r, core_rim, leaf_rim, lumps=16, leaves=45, leaf=0.1, squash=0.7, seed=200 + k)

# a second cap below it, lower left, paler with distance
kit.cap("low", P(100, 330, 25), P(98, 256, 27), 3.6, 3.0, cap_green, moss_far, normal=(0.05, 0.55, 1), ribs=30, ragged=0.16, seed=5, mound=0.1)

# ---- twisted trunks ------------------------------------------------------------------------
kit.trunk("t1", [(28, -22, 21, 15), (58, 10, 20.5, 15), (92, 36, 20, 15), (124, 56, 19.5, 15), (148, 78, 19, 16), (158, 106, 18.6, 16), (161, 140, 18.2, 17), (163, 166, 18, 20), (164, 190, 18, 27)],
          bark, strands=7, twist=1.7, seed=1, rings=140, thick=0.5, spread=0.6)
kit.trunk("t2", [(118, -20, 21, 17), (124, 14, 20.6, 16), (134, 44, 20.2, 15), (146, 70, 19.6, 14), (156, 96, 19, 12)], bark, strands=6, twist=1.1, seed=2, thick=0.5, spread=0.6)
kit.trunk("t3", [(22, -10, 20, 9), (32, 40, 19.6, 9), (44, 90, 19.2, 10), (58, 140, 18.8, 10), (70, 180, 18.5, 13)], bark, strands=5, twist=1.0, seed=3, thick=0.55, spread=0.55)
kit.trunk("t0", [(-14, -10, 24, 10), (-4, 40, 24, 10), (4, 90, 24, 9), (8, 132, 24, 8)], bark, strands=3, twist=0.8, seed=4)
kit.cap("l1", P(4, 168, 24), P(8, 131, 24), 1.25, 1.1, cap_green, moss, normal=(-0.1, 0.1, 1), ribs=14, round_=1.3, seed=6, ragged=0.15)

# ---- the woven mass overhead, upper right ---------------------------------------------------
kit.cap("nest", P(345, 40, 15), P(345, -85, 17), 4.6, 4.4, nest, moss, normal=(0.03, 0.0, 1), ribs=46, rib_amp=0.03, shingles=7, shingle_amp=0.03, round_=3.0, spread_pow=0.6,
        ragged=0.08, swirl=16.0, seed=7, segs=276)
kit.trunk("t4", [(455, -5, 22, 7), (466, 40, 22, 6), (478, 85, 22, 6), (490, 128, 22, 7)], bark_far, strands=3, twist=1.0, seed=5)
kit.cap("r1", P(491, 178, 22), P(474, 124, 22), 1.45, 1.3, cap_green, moss, normal=(-0.12, 0.1, 1), ribs=16, round_=1.25, seed=8, ragged=0.16)

# ---- smaller caps at mid depth: (stem spine, hub px, centre px, d, radius px, material, normal, seed)
def hanging(name, stem, hub, centre, d, rad, mat, normal=(0, 0.1, 1), seed=0, round_=1.2, strands=1, bark_mat=bark_far, ribs=14):
    if stem: kit.trunk(name + "_stem", [(x, y, d, w) for x, y, w in stem], bark_mat, strands=strands, twist=0.8, seed=seed, rings=50, segs=10)
    r = px_radius(centre[0], centre[1], d, rad)
    kit.cap(name, P(hub[0], hub[1], d), P(centre[0], centre[1], d), r, r * 0.9, mat, moss_far, normal=normal, ribs=ribs, round_=round_, seed=seed, ragged=0.16, segs=128, rings=24, mound=0.2)

hanging("c1", [(260, 45, 4), (261, 80, 4), (262, 104, 6)], (250, 130), (264, 103), 28, 27, cap_green, normal=(-0.2, 0.1, 1), seed=11)
hanging("r2", [(431, 40, 5), (432, 60, 5), (433, 80, 10)], (428, 101), (436, 82), 30, 35, cap_teal, normal=(-0.05, 0.12, 1), seed=12)
hanging("r3", [(389, 150, 3), (391, 172, 4), (394, 186, 8)], (392, 207), (396, 187), 26, 27, cap_teal, normal=(0.1, 0.12, 1), seed=13)
hanging("b1", [(106, 60, 2.5), (107, 110, 2.5), (107, 149, 3)], (106, 160), (106, 148), 40, 15, cap_brown, seed=14)
hanging("b2", [(128, 60, 2.5), (128, 100, 2.5), (126, 118, 4)], (118, 136), (118, 118), 50, 23, cap_teal, seed=15)
hanging("b3", [(78, 20, 2), (78, 60, 2), (79, 92, 2.5)], (79, 101), (79, 92), 45, 11, cap_brown, seed=16)
hanging("b4", [(178, 20, 3), (179, 60, 3), (181, 90, 3)], (183, 101), (183, 90), 40, 9, cap_brown, seed=17)
hanging("b5", [(414, 55, 2), (415, 100, 2), (415, 130, 2.5)], (415, 139), (415, 130), 70, 11, cap_teal, seed=18)
hanging("b6", [(437, 100, 2), (438, 130, 2), (437, 160, 3)], (436, 174), (436, 161), 85, 16, cap_teal, seed=19)
hanging("b7", [(22, 40, 2), (22, 80, 2), (23, 120, 2)], (23, 128), (23, 120), 40, 9, cap_brown, seed=20)

# ---- bare stems fading into the haze: (x_top, y_top, x_bot, y_bot, d, half_width)
for i, (x0, y0, x1, y1, d, w) in enumerate([(306, 30, 308, 112, 45, 3), (353, 40, 355, 126, 60, 2.5), (370, 45, 370, 126, 75, 2), (384, 40, 392, 130, 36, 5),
                                            (163, 10, 164, 120, 42, 3), (130, 120, 131, 178, 34, 2), (40, 100, 41, 178, 30, 2), (274, 40, 275, 75, 60, 2),
                                            (296, 60, 296, 150, 90, 2), (330, 90, 331, 160, 95, 2), (455, 60, 456, 150, 100, 3), (200, 30, 201, 130, 70, 2.5),
                                            (225, 20, 226, 110, 90, 2), (60, 20, 61, 100, 80, 2), (92, 30, 92, 90, 70, 2)]):
    kit.trunk("stem", [(x0, y0 - 60, d, w), (x0, y0, d, w), ((x0 + x1) / 2, (y0 + y1) / 2, d, w * 0.9), (x1, y1, d, w * 0.7)], bark_far, strands=1, seed=30 + i, rings=40, segs=8)
# the pale drooping bud under the woven mass
kit.trunk("bud", [(320, 40, 20, 5), (326, 56, 20, 8), (333, 72, 20, 9), (338, 88, 20, 2)], bud, strands=1, seed=60, rings=40, segs=16)

if int(SAMPLES) == 0:
    kit.preview(OUT); print("PREVIEW"); sys.exit(0)

# ---- atmosphere ---------------------------------------------------------------------------
# mist veils hanging among the trunk tops: (px, py, d, radius)
for i, (px, py, d, r) in enumerate([(38, 30, 16, 1.6), (62, 60, 17, 1.2), (228, 40, 26, 2.2), (150, 10, 23, 2.0)]):
    kit.cloud("cloud_mist", P(px, py, d), r, seed=120 + i, stretch=0.7, squash=1.5, density=0.18, emit=0.22, wisp=0.42, edge=0.6, colour=(0.62, 0.62, 0.78))
SUN = (0.5, 0.5, -0.65)
kit.backdrop_haze(0.015, [(0.0, "#a8889a", "#eec8ba"), (0.28, "#927a94", "#dab2ac"), (0.5, "#58566c", "#8a7c92"), (0.68, "#454658", "#5e5e74"), (1.0, "#3a3b4c", "#525468")], lo=-0.26, hi=0.26, cloud=0.75, cloud_scale=9.0, at=(0, 9 + 200, 0))
kit.light(SUN, 2.4, (1.0, 0.86, 0.84), (0.3, 0.3, 0.4), 1.0)
kit.sky([(0.0, "#e8bcb2"), (0.3, "#d2a6aa"), (0.42, "#8a7a94"), (0.52, "#50526a"), (1.0, "#34364a")], strength=0.55, lo=-0.3, hi=0.3)
kit.render(OUT, int(WIDTH), int(SAMPLES))
print("DONE")
