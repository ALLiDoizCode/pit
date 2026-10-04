"""PROTOTYPE: recreation of owner reference scene 7 (green forest floor under giant mossy trunks), no characters."""
import sys, math, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, bpy, bmesh
import kit
from kit import P
from mathutils import Vector, noise
OUT, WIDTH, SAMPLES = sys.argv[sys.argv.index("--") + 1:][:3]
CAMZ = 6.0
kit.setup(860, 483, lens=30, pitch_deg=-8, cam_z=CAMZ)
SUN = Vector((-0.35, -0.5, -0.8)).normalized(); TOSUN = -SUN

def G0(px, py):                       # pixel -> flat ground z=0
    o = Vector(kit.CAM.location); d = (P(px, py, 1) - o).normalized(); return o + d * (-o.z / d.z)

# ---- ground heightfield with a stream channel ----------------------------------------
STREAM = [(170, 200, 1.6), (196, 212, 0.9), (214, 250, 0.6), (246, 296, 0.45), (292, 338, 0.45), (350, 366, 0.7), (430, 384, 1.0), (520, 382, 1.0), (600, 374, 0.8), (680, 366, 0.5), (790, 350, 0.5)]
BRANCH = [(440, 384, 0.5), (478, 418, 0.45), (520, 446, 0.45), (560, 483, 0.5), (600, 540, 0.5)]
def _world(path): return [(G0(px, py).x, G0(px, py).y, w) for px, py, w in path]
SEGS = []
for path in (_world(STREAM), _world(BRANCH)): SEGS += list(zip(path, path[1:]))
MOUNDS = [  # pixel on flat ground, height, radius x, radius y
    (80, 345, 1.0, 7, 6), (60, 250, 1.2, 10, 9), (830, 440, 1.3, 6, 6), (780, 320, 1.2, 8, 7), (420, 310, 0.6, 9, 6),
    (330, 440, 0.5, 5, 4), (560, 250, 0.9, 16, 8), (150, 232, 1.0, 12, 8), (640, 440, 0.6, 5, 4)]
MW = [(G0(px, py).x, G0(px, py).y, h, rx, ry) for px, py, h, rx, ry in MOUNDS]
def stream_dist(X, Y):
    best = np.full(np.shape(X), 1e9)
    for (ax, ay, aw), (bx, by, bw) in SEGS:
        dx, dy = bx - ax, by - ay; t = np.clip(((X - ax) * dx + (Y - ay) * dy) / (dx * dx + dy * dy), 0, 1)
        best = np.minimum(best, np.hypot(X - (ax + dx * t), Y - (ay + dy * t)) - (aw + (bw - aw) * t))
    return best
def H(X, Y):
    h = 0.25 * np.sin(0.11 * X + 1) * np.sin(0.09 * Y + 2) + 0.15 * np.sin(0.23 * X + 0.3 * Y) + 0.08 * np.sin(0.5 * X - 0.41 * Y + 1.3) + 0.06 * np.sin(1.3 * X + 0.7) * np.sin(1.1 * Y)
    for cx, cy, a, rx, ry in MW: h = h + a * np.exp(-(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2))
    k = np.clip(stream_dist(X, Y) / 1.6, 0, 1); k = k * k * (3 - 2 * k)
    return -0.75 + (h + 0.3 + 0.75) * k
def G(px, py): return kit.ground_hit(px, py, H)

ground_mat = kit.rock_material("ground", rock=("#2f8a3c", "#3fa046", "#5cc058"), grass=("#3fa84a", "#6fd060"), grass_from=0.3)
gr = kit.ground("ground", H, ground_mat)
# water
wm = bpy.data.materials.new("water"); wb = wm.node_tree.nodes["Principled BSDF"]
wb.inputs["Base Color"].default_value = (*kit.srgb("#4aa890"), 1); wb.inputs["Roughness"].default_value = 0.12
wb.inputs["Emission Color"].default_value = (*kit.srgb("#4fae98"), 1); wb.inputs["Emission Strength"].default_value = 0.12
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=160); bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 150, -0.5)); kit._obj("water", bm, wm, smooth=False)

# ---- grass blades and flowers ------------------------------------------------------------
rng = np.random.default_rng(1)
def scatter(n, dmin, dmax, half_deg=36):
    a = np.radians(rng.uniform(-half_deg, half_deg, n)); d = dmin * (dmax / dmin) ** rng.uniform(0, 1, n)
    X, Y = np.sin(a) * d, np.cos(a) * d; Z = H(X, Y); e = 0.15
    nx = -(H(X + e, Y) - H(X - e, Y)) / (2 * e); ny = -(H(X, Y + e) - H(X, Y - e)) / (2 * e)
    nrm = np.stack([nx, ny, np.ones(n)], 1); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    return np.stack([X, Y, Z], 1), nrm, d
grass_mat = kit.card_material("grass", "#2a8c48", "#45b05a", "#5cc468", "#84d878", glow=0.03, toward=TOSUN, spread=0.6)
pos, nrm, d = scatter(800000, 6, 150); keep = pos[:, 2] > -0.45
kit.cards("grass", pos[keep], nrm[keep], (0.055 + d[keep] * 0.008), grass_mat, seed=2, mode="blade")
flower_mat = bpy.data.materials.new("flower"); fb = flower_mat.node_tree.nodes["Principled BSDF"]
fb.inputs["Base Color"].default_value = (0.7, 0.7, 0.78, 1); fb.inputs["Emission Color"].default_value = (*kit.srgb("#8fa4f0"), 1); fb.inputs["Emission Strength"].default_value = 0.16
_at = flower_mat.node_tree.nodes.new("ShaderNodeAttribute"); _at.attribute_name = "host_n"; flower_mat.node_tree.links.new(_at.outputs["Vector"], fb.inputs["Normal"]); kit.two_sided(flower_mat.node_tree, fb, (0.7, 0.7, 0.78, 1), _at.outputs["Vector"])
pos, nrm, d = scatter(32000, 6, 110)
mask = np.array([noise.noise(Vector((x * 0.22, y * 0.22, 3.0))) + 0.5 * noise.noise(Vector((x * 0.9, y * 0.9, 7.0))) for x, y, _ in pos])
keep = (mask + rng.uniform(-0.35, 0.35, len(mask)) > 0.1) & (pos[:, 2] > -0.2)
kit.cards("flowers", pos[keep], nrm[keep], 0.017 + d[keep] * 0.002, flower_mat, seed=3, mode="flat", lift=0.22)

# ---- trunks -------------------------------------------------------------------------------
def tr(name, path, mat, leafmat=None, n=0, size=0.3, seed=0, **kw):
    o = kit.trunk(name, [P(px, py, d) for px, py, d, r in path], [r for *_, r in path], mat, seed=seed, **kw)
    if leafmat and n:
        p, nn = kit.surface_points(o, n, seed); kit.cards(name + "_moss", p, nn, size, leafmat, seed=seed, lift=size * 0.3)
    return o
arch_mat = kit.moss_material("arch", "#1f6a44", "#2f8a50", "#46a85c", scale=0.35)
arch_leaf = kit.card_material("arch_leaf", "#1f6e4a", "#35904f", "#62c05a", "#a6ea70", glow=0.03, toward=TOSUN)
dark_mat = kit.moss_material("dark", "#144a38", "#1c6248", "#2a7a56", scale=0.4)
dark_leaf = kit.card_material("dark_leaf", "#16523c", "#216e50", "#2f8a5c", "#4aa868", glow=0.02, toward=TOSUN)
far_mat = kit.moss_material("far", "#1c6a5c", "#2a8270", "#44a484", scale=0.12)
far_leaf = kit.card_material("far_leaf", "#1e6e60", "#2e8a74", "#4cac86", "#7ad09a", glow=0.05, toward=TOSUN)
lit_mat = kit.moss_material("lit", "#2f8a5c", "#44a868", "#62c474", scale=0.15)
lit_leaf = kit.card_material("lit_leaf", "#2f8a60", "#48ac6c", "#6cd07a", "#a0ec8c", glow=0.05, toward=TOSUN)

tr("arch", [(705, 330, 28, 3.4), (700, 190, 30, 2.8), (655, 60, 35, 3.0), (560, -70, 43, 3.4), (455, -50, 52, 4.0), (385, 70, 61, 4.4), (310, 215, 70, 5.2)],
   arch_mat, arch_leaf, 220000, 0.11, seed=1, rings=140, seg=64, rough=0.4)
tr("left_near", [(45, -60, 30, 2.6), (30, 80, 31, 2.5), (22, 170, 32, 2.6), (10, 260, 33, 3.2)], dark_mat, dark_leaf, 40000, 0.16, seed=2)
tr("ledge", [(40, 8, 62, 1.6), (130, 6, 64, 1.5), (230, 18, 66, 1.3)], dark_mat, dark_leaf, 12000, 0.25, seed=3, rings=40)
tr("right_far", [(840, 220, 60, 4.5), (820, 90, 62, 4), (790, -40, 64, 4)], far_mat, far_leaf, 20000, 0.4, seed=4)
tr("diag", [(215, 215, 84, 3.5), (265, 100, 88, 3.2), (335, -30, 92, 3.5)], lit_mat, lit_leaf, 25000, 0.45, seed=5)
tr("far1", [(535, 215, 120, 6), (505, 100, 125, 5.5), (470, -40, 130, 5.5)], far_mat, far_leaf, 20000, 0.7, seed=6)
tr("far2", [(620, 210, 150, 7), (575, 80, 150, 6.5), (610, -50, 150, 7)], far_mat, far_leaf, 20000, 0.8, seed=7)
tr("far3", [(410, 205, 175, 8), (455, 60, 175, 7.5), (425, -60, 175, 8)], far_mat, far_leaf, 20000, 0.9, seed=8)
tr("far4", [(760, 215, 110, 5), (700, 120, 112, 4.5), (720, -40, 116, 5)], far_mat, far_leaf, 15000, 0.6, seed=9)
tr("far5", [(-20, 210, 120, 7), (60, 60, 122, 6), (40, -60, 125, 6)], far_mat, far_leaf, 15000, 0.7, seed=10)
tr("far6", [(300, 210, 140, 5), (250, 90, 142, 5), (290, -50, 145, 5.5)], far_mat, far_leaf, 15000, 0.7, seed=11)
tr("far7", [(680, 212, 200, 8), (720, 60, 200, 8), (660, -60, 200, 8)], far_mat, far_leaf, 15000, 1.0, seed=12)
tr("far8", [(480, 210, 95, 2.2), (560, 150, 97, 2.0), (610, 60, 100, 2.2), (590, -40, 104, 2.5)], far_mat, far_leaf, 12000, 0.5, seed=13)
# wall behind the waterfall, and a closing backdrop
wall = kit.cliff("wall", [(70, -60, 82), (140, -60, 80), (230, -60, 84)], [(70, 215, 82), (140, 215, 80), (230, 215, 84)], lit_mat, back=20, rough=0.6, seed=3)
p, nn = kit.surface_points(wall, 30000, 4); kit.cards("wall_moss", p, nn, 0.4, lit_leaf, seed=4, lift=0.1)
kit.cliff("backdrop", [(-80, -200, 260), (430, -200, 250), (940, -200, 260)], [(-80, 230, 260), (430, 230, 250), (940, 230, 260)], far_mat, back=30, rough=1.0, seed=5)
# bushy root mound right of the arch
core = kit.flat_material("core", "#1a5a3a"); bush_leaf = kit.leaf_material("bush", "#22704a", "#3f9a55", "#6cc864", "#a8ec78", glow=0.07)
for i, (px, py, d, r) in enumerate([(820, 240, 30, 3.6), (760, 285, 29, 1.8), (640, 300, 30, 1.2), (858, 150, 34, 3.0)]):
    kit.foliage("bush", P(px, py, d), r, core, bush_leaf, lumps=50, leaves=110, leaf=0.06, seed=20 + i)

# ---- waterfall and mist --------------------------------------------------------------------
wf = bmesh.new(); a, b = P(132, 10, 64), P(140, 192, 64)
vs = [wf.verts.new(a + Vector((-0.9, 0, 0))), wf.verts.new(a + Vector((0.9, 0, 0))), wf.verts.new(b + Vector((1.8, 0, 0))), wf.verts.new(b + Vector((-1.8, 0, 0)))]; wf.faces.new(vs)
wfm = bpy.data.materials.new("fall"); nt = wfm.node_tree; b_ = nt.nodes["Principled BSDF"]
geo = nt.nodes.new("ShaderNodeNewGeometry"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.5, 2.5, 0.08); nt.links.new(geo.outputs["Position"], mp.inputs[0])
nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 4; nt.links.new(mp.outputs[0], nz.inputs["Vector"])
c = kit._ramp(nt, nz.outputs[0], [(0.35, "#9fe0c8"), (0.6, "#f4fff8")]); nt.links.new(c, b_.inputs["Base Color"]); nt.links.new(c, b_.inputs["Emission Color"]); b_.inputs["Emission Strength"].default_value = 1.0
kit._obj("waterfall", wf, wfm, smooth=False)
for i, (px, py, r) in enumerate([(150, 188, 3.2), (185, 196, 2.6), (120, 186, 2.2)]):
    kit.cloud("mist", P(px, py, 62), r, density=0.5, seed=60 + i, squash=0.6, stretch=1.3)

# ---- standing stones ------------------------------------------------------------------------
stone_mat = kit.moss_material("stone", "#2a6a40", "#36804c", "#4a9a5a", scale=1.5, top="#62bc62")
STONES = [(12, 483, 140), (60, 486, 42), (120, 486, 32), (245, 482, 76), (155, 410, 66), (335, 400, 56), (190, 356, 56), (205, 356, 44), (130, 326, 46), (92, 300, 40), (45, 297, 38),
          (515, 440, 46), (605, 405, 42), (630, 398, 35), (680, 375, 28), (770, 400, 56), (712, 486, 46), (745, 486, 22),
          (460, 322, 25), (400, 318, 18), (380, 318, 18), (440, 300, 12), (480, 297, 12), (512, 298, 20), (555, 290, 15), (570, 292, 18), (455, 270, 14), (470, 270, 14),
          (492, 265, 10), (518, 262, 22), (410, 260, 14), (385, 255, 18), (340, 243, 18), (300, 262, 18), (235, 247, 12), (250, 247, 14), (108, 222, 22), (125, 224, 16), (460, 243, 10), (358, 240, 12)]
rnd = random.Random(7)
for i, (px, py, hp) in enumerate(STONES):
    g = G(px, min(py, 478)); dist = (g - kit.CAM.location).length; hgt = 1.15 * hp * dist / 716.7
    if py > 478: g = g - Vector((0, 0, (py - 478) * dist / 716.7))
    kit.stone("stone", g, hgt, hgt * rnd.uniform(0.42, 0.58), stone_mat, lean=(rnd.uniform(-.15, .15), rnd.uniform(-.1, .1)), seed=i)

# ---- drifting petals ---------------------------------------------------------------------------
pm = bpy.data.materials.new("petal"); pb = pm.node_tree.nodes["Principled BSDF"]; pb.inputs["Base Color"].default_value = (1, 0.9, 0.95, 1)
pb.inputs["Emission Color"].default_value = (1, 0.88, 0.95, 1); pb.inputs["Emission Strength"].default_value = 0.9
PET = [(398, 122, 9), (396, 186, 10), (438, 212, 6), (808, 348, 8), (240, 232, 5), (286, 8, 2), (476, 68, 2), (612, 64, 2), (810, 40, 3), (538, 190, 3), (500, 232, 2), (32, 228, 3), (66, 302, 4), (210, 136, 4), (518, 444, 5), (790, 14, 3), (478, 290, 4), (300, 180, 2), (680, 110, 2), (150, 60, 2), (590, 300, 3), (740, 250, 2), (330, 60, 2), (90, 380, 3)]
pp = np.array([P(px, py, 9 + (i * 7) % 14) for i, (px, py, s) in enumerate(PET)]); ps = np.array([s * (9 + (i * 7) % 14) / 716.7 * 0.8 for i, (_, _, s) in enumerate(PET)])
kit.cards("petals", pp, np.tile(np.array([[0, -0.8, 0.6]]), (len(pp), 1)), ps, pm, seed=5, mode="leaf")

# ---- shade from the unseen canopy, light, haze ------------------------------------------------
for i, (px, py, r) in enumerate([(120, 440, 9), (330, 470, 5), (40, 380, 6), (600, 335, 6), (380, 262, 4)]):
    kit.shadow_disc(SUN, G(px, py), r, seed=i)
import os
if not os.environ.get('NOFOG'): kit.fog(0.0015, (0.4, 0.92, 0.8), size=(1200, 900, 110), at=(0, 350, 35))
SUN_E = float(os.environ.get("SUN_E", 5.5)); SKY_E = float(os.environ.get("SKY_E", 0.3))
kit.light(SUN, SUN_E, (1.0, 0.98, 0.8), kit.srgb("#7fe0c0"), SKY_E)
if os.environ.get('RAYS'):
    dg = bpy.context.evaluated_depsgraph_get()
    for px, py in [(100, 430), (430, 300), (700, 420), (300, 240), (600, 240), (430, 440)]:
        g = G(px, py) + Vector((0, 0, 1.5)); print('RAY', px, py, [round(v, 1) for v in g], end=' ')
        for k in range(4):
            hit, loc, n, idx, ob, _ = kit.scene.ray_cast(dg, g, TOSUN)
            if not hit: print('| clear', end=''); break
            print('|', ob.name, round((loc - g).length, 1), end=''); g = loc + TOSUN * 0.05
        print()
    sys.exit(0)
kit.render(OUT, int(WIDTH), int(SAMPLES))
print("DONE")
