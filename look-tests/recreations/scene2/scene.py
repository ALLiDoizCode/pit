"""PROTOTYPE: recreation of owner reference scene 2 (town on the rim of a great pit), without characters."""
import sys, math, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import kit
from kit import P, H, cliff
from mathutils import Vector
OUT, WIDTH, SAMPLES = sys.argv[sys.argv.index("--") + 1:][:3]
kit.setup(500, 281, lens=35, pitch_deg=-14.8)
CAM = kit.CAM
SUN = Vector((-0.5, 0.55, -0.67)).normalized()

def interp(tab, x):
    for (x0, *a), (x1, *b) in zip(tab, tab[1:]):
        if x <= x1: f = min(1, max(0, (x - x0) / (x1 - x0))); return [p + (q - p) * f for p, q in zip(a, b)]
    return list(tab[-1][1:])

# ---- the far wall of the pit: lip traced from the reference, (px, py, distance)
LIP = [(-30, 74, 760), (50, 80, 860), (105, 83, 930), (194, 81, 1000), (250, 82, 1010), (305, 83, 1000), (389, 86, 960), (450, 90, 900), (530, 97, 820)]
SKY = [(-30, 46), (0, 44), (30, 40), (55, 36), (83, 31), (117, 36), (140, 33), (167, 33), (195, 30), (222, 31), (250, 34), (278, 35), (305, 33), (333, 36), (370, 38), (417, 42), (460, 43), (500, 46), (530, 48)]
def lip_at(px): return interp(LIP, px)                      # -> [py, d]
def wall_d(px, py, off=0.0):
    """Distance to the (vertical) far wall along the ray through (px, py)."""
    ly, ld = lip_at(px); w = P(px, ly, ld) - CAM.location; hd = math.hypot(w.x, w.y) - off
    v = P(px, py, 1.0) - CAM.location; return hd / math.hypot(v.x, v.y)

wall_m = kit.rock_material("wall", rock=("#282624", "#7a7462", "#a0987f"), grass=("#7a7462", "#8c8672"), grass_from=0.93, streak=1.4, patch="#5a5348", patch_scale=0.006)
ridge_m = kit.rock_material("ridge", rock=("#504c66", "#787880", "#929196"), grass=("#787a7a", "#8a8a86"), grass_from=0.9, streak=0.5, moss="#5f7460", patch_scale=0.004, grass_scale=0.02)
cliff("wall", LIP, [(x, 300, wall_d(x, 300)) for x, _, _ in LIP], wall_m, back=90, rise=4, rough=0.22, seed=1, jag=0.0, cols=260, rows=90)
cliff("ridge", [(x, y, lip_at(x)[1] + 330) for x, y in SKY], [(x, y + 2, d + 110) for x, y, d in LIP], ridge_m, back=200, rise=-60, rough=0.28, seed=2, jag=0.5, cols=260, rows=50)

# ---- the town on the far rim: hundreds of tiny buildings dropped onto the slope by ray cast
rnd = random.Random(7); items = []
for i in range(1700):
    px = rnd.uniform(40, 505); ly = lip_at(px)[0]
    dens = 1.0 if px > 110 else (px - 40) / 70
    if rnd.random() > dens: continue
    py = ly - 1 - 27 * rnd.random() ** 1.7
    loc, nrm = kit.hit(px, py)
    if loc is None or loc.y < 500: continue
    s = rnd.uniform(3.0, 6.0)
    items.append((loc, s, s * rnd.uniform(0.7, 1.4), s * rnd.uniform(0.6, 1.2), s * rnd.uniform(0.35, 0.6), rnd.uniform(0, math.pi)))
kit.houses("town", items, kit.varied_material("town_wall", ["#c8c0ae", "#b4aa96", "#d8d2c4", "#a49a88", "#bcb6a8"]),
           kit.varied_material("town_roof", ["#8a7a68", "#a09078", "#7c7c78", "#94705a", "#6f7c70", "#b0a48c", "#84746a", "#9c988c"]))
print("town houses", len(items))
# small dark trees standing on the skyline and scattered in the town
tree_core = kit.flat_material("tree_core", "#3a4a44"); tree_leaf = kit.leaf_material("tree_leaf", "#3c4c48", "#51655a", "#6a8068", "#84987c", glow=0.03)
for i, (px, py) in enumerate([(55, 36), (75, 31), (108, 36), (168, 33), (222, 31), (288, 35), (298, 34), (335, 36), (405, 41), (430, 43)]):
    loc, _ = kit.hit(px, py + 4)
    if loc: kit.foliage("sky_tree", loc + Vector((0, 0, 4)), rnd.uniform(3, 5), tree_core, tree_leaf, lumps=10, leaves=30, leaf=0.25, squash=1.3, seed=i)
for i in range(40):
    px = rnd.uniform(60, 500); loc, _ = kit.hit(px, lip_at(px)[0] - rnd.uniform(3, 24))
    if loc: kit.foliage("town_tree", loc + Vector((0, 0, 3)), rnd.uniform(5, 10), tree_core, tree_leaf, lumps=8, leaves=30, leaf=0.25, squash=0.7, seed=100 + i)

# ---- waterfalls down the far wall
water = kit.emit_material("water", "#e4ecf4"); mist = kit.puff_material("mist", "#b8c4d8", "#d8e0ec", "#f4f6fa", emit=0.5)
for i, (px, y0, y1, w0, w1) in enumerate([(232, 83, 186, 1.5, 3.4), (362, 86, 192, 1.5, 3.8), (440, 92, 190, 1.2, 3.2), (470, 96, 216, 1.3, 3.4), (488, 100, 150, 0.7, 1.4), (300, 110, 150, 0.6, 1.2)]):
    pts = [(px - w0 / 2, y0), (px + w0 / 2, y0), (px + w1 / 2 + 0.6, y1), (px - w1 / 2 + 0.6, y1)]
    kit.card_px("fall", [(x, y, wall_d(x, y, 70)) for x, y in pts], water)
    if w1 > 2: kit.cloud("fall_mist", P(px + 0.6, y1 - 3, wall_d(px, y1, 85)), 20, density=0.8, seed=i, squash=0.9, stretch=1.0)

# ---- the rim's shadow lying across the far wall (lower part and left side), painted with an unseen card
SH = [(-60, 36), (30, 46), (80, 66), (112, 78), (150, 96), (190, 122), (240, 150), (300, 170), (380, 184), (460, 192), (540, 196), (540, 330), (-60, 330)]
SHT = SH[:-2]
for (xa, ya), (xb, yb) in zip(SHT, SHT[1:]):
    for k in range(4):      # strips of quads, so the card follows the wall and never folds
        f0, f1 = k / 4, (k + 1) / 4; q = [(xa, ya + (310 - ya) * f0), (xb, yb + (310 - yb) * f0), (xb, yb + (310 - yb) * f1), (xa, ya + (310 - ya) * f1)]
        kit.shadow_card([(x, y, wall_d(min(max(x, -30), 530), y, 40)) for x, y in q], SUN, t=160)

# blue-violet mist lying at the foot of the wall
pmist = kit.puff_material("pit_mist", "#1e2638", "#2c3454", "#444e7c", emit=0.1)
for i, (px, py) in enumerate([(200, 226), (240, 222), (285, 220), (330, 222), (372, 218), (415, 216), (460, 218), (505, 214), (150, 232), (100, 236)]):
    kit.puff("pit_mist", P(px, py + 8, 640), 40, pmist, n=40, squash=0.22, lump=(0.3, 0.5), seed=i, stretch=(1.6, 1.2, 1))

# ---- sea and sky
kit.sea(300, "#4f86a8", "#7ba5bd", "#a6c0cf", glare=("#cddde4", -0.3, 0.2))

# ---- near rim, left: a slope crowded with roofs, junk and bushes
near_m = kit.rock_material("near", rock=("#2c2a26", "#4a4438", "#6a5f4c"), grass=("#3a4f3c", "#5c7a52"), grass_from=0.7, grass_scale=0.4)
LT = [(-30, 186), (30, 190), (80, 196), (120, 206), (160, 219), (195, 232), (225, 246)]
def lt_at(px): return interp(LT, px)[0]
lipL = [(x, y, 118 - (y - 186) * 0.5) for x, y in LT]
cliff("near_l", lipL, [(x, 330, 55) for x, _, _ in lipL], near_m, back=6, rise=-3, rough=0.5, seed=5, jag=1.2)
wallc = ["#c4b8a0", "#a89c84", "#988c78", "#cfc6b0", "#8c8068"]; roofc = ["#a8905a", "#7a5844", "#8f6850", "#6f5a4c", "#9a8468", "#6a6258", "#84705c", "#5c5450"]
hw, hr = kit.varied_material("near_wall", wallc), kit.varied_material("near_roof", roofc)
items = []; rnd = random.Random(4)
for i in range(70):
    px = rnd.uniform(-5, 205); top = lt_at(px); py = rnd.uniform(top + 1, max(top + 6, 247 - px * 0.06)); d = 112 - (py - 186) * 0.75
    w = rnd.uniform(1.8, 3.6); h = w * rnd.uniform(0.6, 1.3); rh = w * rnd.uniform(0.4, 0.9)
    items.append((P(px, py, d - 14) - Vector((0, 0, h + rh)), w, w * rnd.uniform(0.8, 1.4), h, rh, rnd.uniform(0, math.pi)))
kit.houses("near_l_houses", items, hw, hr)
core_g = kit.flat_material("core_g", "#27452f"); leaf_g = kit.leaf_material("leaf_g", "#2c5238", "#44794c", "#62a062", "#8cc47c", glow=0.06)
for i in range(13):
    px = rnd.uniform(-5, 200); top = lt_at(px); py = rnd.uniform(top + 8, 250 - px * 0.06); d = 108 - (py - 186) * 0.75
    kit.foliage("bush_l", P(px, py, d), rnd.uniform(1.6, 3.6), core_g, leaf_g, lumps=26, leaves=60, leaf=0.14, squash=0.7, seed=300 + i)
wood = kit.emit_material("wood", "#9a8460", vary=0.25, scale=0.3)
for (x0, y0, x1, y1) in [(2, 205, 26, 194), (40, 212, 66, 197), (58, 200, 62, 216), (88, 213, 104, 205), (93, 198, 95, 222), (112, 222, 118, 208), (20, 214, 24, 198), (70, 222, 96, 219)]:
    dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy); nx, ny = -dy / L * 0.8, dx / L * 0.8
    kit.card_px("beam", [(x0 - nx, y0 - ny, 70), (x1 - nx, y1 - ny, 70), (x1 + nx, y1 + ny, 70), (x0 + nx, y0 + ny, 70)], wood)

# ---- near rim, right: a few roofs and a bush showing over the terrace edge
items = []
for px, py, w in [(352, 229, 2.6), (368, 226, 2.4), (380, 222, 1.8), (395, 225, 2.8), (408, 224, 2.4), (418, 219, 1.6), (455, 217, 5.4), (486, 222, 3.4), (500, 219, 3.0), (432, 226, 2.6)]:
    h, rh = w * 0.7, w * 0.6; items.append((P(px, py, 78) - Vector((0, 0, h + rh)), w, w * 1.3, h, rh, rnd.uniform(-0.5, 0.5) + math.pi / 2))
kit.houses("near_r_houses", items, hw, hr)
for i, (px, py, r) in enumerate([(441, 228, 2.4), (476, 232, 2.0), (425, 234, 1.5), (498, 232, 1.8)]):
    kit.foliage("bush_r", P(px, py, 72), r, core_g, leaf_g, lumps=26, leaves=70, leaf=0.13, squash=0.8, seed=400 + i)

# ---- foreground paving: a stone terrace on the right, brick steps climbing to it from the left
stone = kit.stone_material("stone", "#94805e", "#bca27c", "#3a352c", scale=0.55, angle=0.15)
brick = kit.stone_material("brick", "#9a8264", "#c0a284", "#3a3028", scale=2.2, angle=0.6)
kit.slab("terrace_l", [(238, 229), (300, 230), (347, 229), (347, 320), (215, 320)], 2.2, 1.5, stone)
kit.slab("terrace_r", [(344, 238), (420, 237), (530, 236), (530, 320), (344, 320)], 2.0, 1.5, stone)
N = 9; x0s = [-95 + i * (238 + 95) / N for i in range(N + 1)]
def step_top(x): return 248 - (x / 238) * 18 if x > 0 else 248 - x * 0.05
for i in range(N):
    a, b = x0s[i], x0s[i + 1] - 0.8
    kit.slab("step", [(a, step_top(a)), (b, step_top(b)), (b + 100, step_top(b) + 72), (a + 100, step_top(a) + 72)], 2.25 + 0.08 * (N - i), 0.6, brick)

# ---- masts, a wire and white flags at the left
mast = kit.emit_material("mast", "#8e9cae"); flag = kit.emit_material("flag", "#eceeee")
for px, y0, y1 in [(15, 100, 204), (52, 92, 200), (105, 95, 214)]:
    kit.card_px("mast", [(px - 0.6, y0, 45), (px + 0.6, y0, 45), (px + 0.6, y1, 45), (px - 0.6, y1, 45)], mast)
kit.card_px("wire", [(52, 93, 45), (105, 96, 45), (105, 96.6, 45), (52, 93.6, 45)], mast)
kit.card_px("flag", [(-6, 97, 44), (18, 98, 44), (38, 103, 44), (55, 110, 44), (40, 114, 44), (24, 124, 44), (6, 125, 44), (-6, 121, 44)], flag)

# ---- white flowers and leaves, bottom right; loose petals on the wind
pet_m = kit.varied_material("petal", ["#f4f4ee", "#e4e6de", "#ffffff", "#d8dcd4"], emit=0.35)
lf_m = kit.varied_material("fl_leaf", ["#2a6a38", "#3f8a46", "#1c4c2c", "#58a45a", "#34783e"], emit=0.05)
K = 2 * (18.0 / 35) * 1.6 / 500     # metres per reference pixel at 1.6 m
for i, (px, py, r) in enumerate([(428, 236, 13), (468, 259, 14), (383, 251, 11), (316, 262, 7), (352, 276, 8), (452, 281, 9), (495, 272, 10)]):
    kit.flower("flower", P(px, py, 1.6), r * K * 1.25, pet_m, lf_m, seed=i)
kit.petals("fl_leaves", [(P(rnd.uniform(300, 505), rnd.uniform(252, 292), rnd.uniform(1.72, 1.95)), rnd.uniform(9, 15) * K, rnd.uniform(6, 9) * K) for _ in range(34)], lf_m, seed=3)
K3 = 2 * (18.0 / 35) * 3.0 / 500
kit.petals("drift", [(P(px, py, 3.0), L * K3, L * K3 * 0.42) for px, py, L in [(375, 28, 22), (458, 27, 10), (497, 30, 10), (200, 62, 15), (410, 90, 9), (455, 165, 9), (402, 217, 10), (322, 14, 4), (132, 97, 4), (230, 152, 3), (275, 110, 3), (100, 272, 12), (238, 35, 3), (340, 128, 3), (60, 235, 3)]], kit.emit_material("drift", "#f2f3f0"), seed=5)

kit.fog(0.0003, (0.22, 0.32, 0.8), size=(2600, 1500, 900), at=(0, 520, -625), anisotropy=0.0)
kit.fog(0.00007, (0.72, 0.82, 0.95), size=(5000, 3600, 1500), at=(0, 1500, -745))
kit.light(SUN, 6.0, (1.0, 0.95, 0.85), (0.6, 0.75, 0.95), 1.0)
kit.sky("#a4c0ea", "#f4f6f8", "#5a94cc", "#8fb4d8", strength=0.85, band_amount=0.8, stretch=(6, 6, 260), elev=(0.0, 0.012, 0.06), seed=1.0)
kit.render(OUT, int(WIDTH), int(SAMPLES))
print("DONE")
