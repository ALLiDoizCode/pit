"""PROTOTYPE: recreation of owner reference scene 9 (back-lit forest clearing), no character / creature / UI."""
import sys, math, random, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, bpy, bmesh
import kit
from kit import P, pal, nz
from mathutils import Vector, Matrix, noise
OUT, WIDTH, SAMPLES = sys.argv[sys.argv.index("--") + 1:][:3]
E = lambda k, d: float(os.environ.get(k, d))
CAMZ = 1.4
kit.setup(500, 281, lens=28, pitch_deg=6, cam_z=CAMZ)
PX = 2 * (18 / 28) / 500                     # metres per reference pixel, per metre of distance
SUN = Vector((0.10, -0.80, -0.60)).normalized(); TOSUN = -SUN; TS = np.array(TOSUN)
rng = np.random.default_rng(1)

# ---- ground: a gentle crest about 15 m out, falling away into the sunlit clearing ----------------
def H(X, Y):
    h = 0.12 * np.sin(0.45 * X + 1) * np.sin(0.37 * Y + 2) + 0.06 * np.sin(1.1 * X + 0.9 * Y)
    side = np.clip((np.abs(X + 0.5) - 2.5) / 5.0, 0, 1); h = h + 0.9 * side * side          # banks at both sides
    k = np.clip((Y - 15) / 14, 0, 1); h = h - 2.6 * k * k * (3 - 2 * k)
    return h
gm = bpy.data.materials.new("ground"); nt = gm.node_tree; gb = nt.nodes["Principled BSDF"]; gb.inputs["Roughness"].default_value = 1
geo = nt.nodes.new("ShaderNodeNewGeometry"); n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.5; n1.inputs["Detail"].default_value = 5
nt.links.new(geo.outputs["Position"], n1.inputs["Vector"]); nt.links.new(kit._ramp(nt, n1.outputs[0], [(0.3, "#46382a"), (0.55, "#726040"), (0.75, "#988456")]), gb.inputs["Base Color"])
kit.ground("ground", H, gm, hfov_deg=84, near=2.0, far=140, na=200, nd=200)

def scatter(n, dmin, dmax, half_deg=40):
    a = np.radians(rng.uniform(-half_deg, half_deg, n)); d = dmin * (dmax / dmin) ** rng.uniform(0, 1, n)
    X, Y = np.sin(a) * d, np.cos(a) * d; return np.stack([X, Y, H(X, Y)], 1), d
UP = np.array([[0, 0, 1.0]])
# grass: big ochre blades, colour grouped into broad patches (painted by script), lit by the real sun
grass_mat = kit.paint_material("grass", glow=E("GRASS_GLOW", 0.10), trans=0.9)
pos, d = scatter(170000, 3.5, 60)
t = 0.50 + 0.5 * np.exp(-(((pos[:, 0] - 0.6) / 3.5) ** 2 + ((pos[:, 1] - 14) / 5.0) ** 2)) + 0.28 * nz(pos, 0.9, 3) + 0.22 * nz(pos, 3.1, 4) + rng.uniform(-0.12, 0.12, len(pos))
t = np.round(t * 5) / 5 * 0.7 + t * 0.3
gcol = pal(t, ["#3e2f28", "#5f4f36", "#85704a", "#a89464", "#d0c090", "#f0e8c8"])
lean = np.tile(UP, (len(pos), 1)) + np.stack([0.5 * nz(pos, 0.5, 8), 0.25 * nz(pos, 0.6, 9) - 0.2, np.zeros(len(pos))], 1)
kit.cards("grass", pos, lean, 0.46 + d * 0.016, grass_mat, seed=2, mode="blade", col=gcol, width=0.5)
# taller tufts catching light along the crest and at the sides
pos, d = scatter(16000, 5, 22)
keep = nz(pos, 0.7, 12) + rng.uniform(-0.3, 0.3, len(pos)) > 0.25; pos, d = pos[keep], d[keep]
t = 0.55 + 0.3 * nz(pos, 1.3, 5) + rng.uniform(-0.15, 0.15, len(pos))
kit.cards("tufts", pos, np.tile(UP, (len(pos), 1)) + rng.uniform(-0.5, 0.5, (len(pos), 3)), 0.5 + d * 0.012, grass_mat, seed=3, width=0.45, mode="blade", col=pal(t, ["#4a3e2c", "#76653e", "#a08c58", "#c8b680", "#ece0b8"]))

# ---- bark -------------------------------------------------------------------------------------
def bark(name, dark, mid, light, scale=3.0):
    m = bpy.data.materials.new(name); nt = m.node_tree; b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 1
    geo = nt.nodes.new("ShaderNodeNewGeometry"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 1, 0.22); nt.links.new(geo.outputs["Position"], mp.inputs[0])
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 3; nt.links.new(mp.outputs[0], n.inputs["Vector"])
    c = kit._ramp(nt, n.outputs[0], [(0.38, dark), (0.5, mid), (0.66, light)])
    for e in c.node.color_ramp.elements: pass
    c.node.color_ramp.interpolation = "CONSTANT"                      # flat painted bands, not gradients
    nt.links.new(c, b.inputs["Base Color"]); nt.links.new(c, b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 0.35
    return m
def tr(name, path, mat, seed=0, **kw):
    return kit.trunk(name, [P(px, py, d) for px, py, d, r in path], [r for *_, r in path], mat, seed=seed, **kw)
bark_near = bark("bark_near", "#2f2320", "#4a3229", "#6e5040")
bark_far = bark("bark_far", "#6a5240", "#8a6c50", "#aa8a66", scale=1.5)
bark_right = bark("bark_right", "#4a3a30", "#5e4a3c", "#7a624c", scale=1.5)
bark_black = bark("bark_black", "#120c0b", "#1e1614", "#2e2420")

# the big left tree: buttressed base, leaning trunk, a knobbed branch to the right, forks into the canopy
tr("L_trunk", [(66, 262, 9, 1.0), (78, 215, 9, 0.76), (88, 165, 9, 0.66), (99, 110, 9, 0.6), (114, 62, 9.1, 0.55), (126, 10, 9.3, 0.5), (126, -50, 9.5, 0.45)], bark_near, seed=1, rough=0.34, twist=3)
for i, (px, py, r) in enumerate([(30, 262, 0.3), (120, 258, 0.28), (62, 275, 0.3)]):
    tr("L_root", [(84, 200, 9, 0.38), ((84 + px) / 2, 240, 9 - 0.3 * i, r), (px, py + 14, 8.6 - 0.4 * i, r * 0.5)], bark_near, seed=20 + i, rings=30, seg=20)
tr("L_branch", [(98, 140, 9, 0.30), (120, 128, 9.2, 0.27), (148, 124, 9.5, 0.24), (168, 120, 9.8, 0.23), (182, 108, 10.0, 0.10)], bark_near, seed=2, rings=50, seg=24, rough=0.4, twist=4)
tr("L_fork1", [(108, 86, 9, 0.30), (80, 50, 8.6, 0.24), (48, 22, 8.2, 0.18), (20, -10, 8, 0.12)], bark_near, seed=3, rings=40, seg=20)
tr("L_fork2", [(120, 50, 9.1, 0.28), (160, 20, 9.6, 0.2), (200, -5, 10, 0.14)], bark_near, seed=4, rings=40, seg=20)
# dark mass at the far left edge (a second, nearer trunk)
tr("L_edge", [(-40, 290, 5.5, 0.6), (-22, 190, 5.6, 0.5), (-8, 100, 5.8, 0.45), (-15, 0, 6, 0.42), (-20, -60, 6.2, 0.4)], bark("bark_edge", "#221d1d", "#352c2b", "#463a36"), seed=5, rough=0.4)
# near dark limb crossing the top right corner
tr("R_limb", [(395, -40, 5.0, 0.30), (425, 2, 5.0, 0.27), (462, 42, 5.0, 0.25), (500, 88, 5.0, 0.24), (540, 140, 5.0, 0.24)], bark_black, seed=6, rings=50, seg=24, rough=0.4)
tr("R_limb2", [(455, 34, 5.0, 0.2), (480, 20, 4.8, 0.16), (520, 10, 4.6, 0.14)], bark_black, seed=7, rings=30, seg=18)
# back-lit tree behind the left tree, and the hazy trees on the right
tr("M_trunk", [(126, 232, 15, 0.42), (132, 190, 15, 0.34), (138, 150, 15.2, 0.3), (158, 105, 15.6, 0.24), (185, 70, 16, 0.16)], bark_far, seed=8, rings=50, seg=24)
#tr("M_branch", [(140, 150, 15.2, 0.2), (175, 135, 15.5, 0.16), (215, 128, 16, 0.1)], bark_far, seed=9, rings=30, seg=16)
tr("R_trunk1", [(398, 232, 17, 0.42), (402, 190, 17, 0.34), (410, 150, 17.2, 0.28), (400, 110, 17.5, 0.2)], bark_right, seed=10, rings=40, seg=20)
tr("R_trunk2", [(452, 236, 15, 0.4), (446, 190, 15, 0.33), (450, 140, 15.2, 0.27), (462, 100, 15.5, 0.2)], bark_right, seed=11, rings=40, seg=20)
tr("R_trunk3", [(362, 228, 22, 0.35), (366, 185, 22, 0.3), (360, 150, 22, 0.22)], bark_right, seed=12, rings=30, seg=16)

# ---- foliage: layered flattened pads of camera-facing brush dabs, coloured in broad patches -----
def canopy(name, clumps, palette, mat, core_mat, n=420, dab_px=9, sub=6, seed=0, lit=None, lit_mat=None, lit_thr=0.42, lit_px=0.7, sunw=0.32, flat=0.42, droop=0.7):
    r_ = np.random.default_rng(seed); core = bmesh.new(); Pp, Nn, Ss, Al = [], [], [], []
    for (px, py, d, r) in clumps:
        c0 = np.array(P(px, py, d))
        for s in range(sub):
            off = r_.normal(size=3) * r * 0.5; off[2] *= 0.7
            rad = np.array([r * r_.uniform(0.45, 0.8), r * r_.uniform(0.45, 0.8), r * r_.uniform(flat * 0.6, flat)]); c = c0 + off
            res = bmesh.ops.create_icosphere(core, subdivisions=1, radius=1.0)
            for v in res["verts"]: v.co = Vector(c) + Vector((v.co.x * rad[0], v.co.y * rad[1], v.co.z * rad[2])) * 0.72
            dr = r_.normal(size=(n, 3)); dr /= np.linalg.norm(dr, axis=1, keepdims=True)
            p = c + dr * rad * r_.uniform(0.8, 1.1, (n, 1)); p[:, 2] -= r * droop * 0.5 * r_.uniform(0, 1, n) ** 3 * (np.abs(dr[:, 2]) < 0.5)     # edges drape
            nn = dr / rad; nn /= np.linalg.norm(nn, axis=1, keepdims=True)
            al = np.stack([dr[:, 0], dr[:, 1], np.full(n, -droop)], 1)
            Pp.append(p); Nn.append(nn); Ss.append(np.full(n, dab_px * PX * d)); Al.append(al)
    kit._obj(name + "_core", core, core_mat, smooth=True)
    p, nn, ss, al = np.concatenate(Pp), np.concatenate(Nn), np.concatenate(Ss), np.concatenate(Al)
    sc = 2.2 / np.mean([c[3] for c in clumps])
    t = 0.42 + sunw * (nn @ TS) + 0.26 * nz(p, sc, seed + 1) + 0.14 * nz(p, sc * 3, seed + 2) + r_.uniform(-0.08, 0.08, len(p))
    k = len(palette) - 1; t = np.round(t * k) / k * 0.75 + t * 0.25                    # group into flat colour steps
    col = pal(t, palette)
    if lit:
        m = (0.6 * nz(p, sc * 1.3, seed + 5) + 0.4 * nz(p, sc * 3.5, seed + 6) + 0.25 * (nn @ TS) + r_.uniform(-0.1, 0.1, len(p))) > lit_thr
        tl = 0.5 + 0.4 * nz(p[m], sc * 4, seed + 7) + r_.uniform(-0.2, 0.2, m.sum())
        kit.dabs(name + "_lit", p[m] + nn[m] * 0.03, nn[m], ss[m] * lit_px, lit_mat, col=pal(tl, lit), seed=seed + 3, along=al[m], aspect=1.6)
        p, nn, ss, al, col = p[~m], nn[~m], ss[~m], al[~m], col[~m]
    return kit.dabs(name, p, nn, ss, mat, col=col, seed=seed, along=al, aspect=1.7)

dark_mat = kit.paint_material("leaf_dark", glow=E("DARK_GLOW", 0.4), trans=0.6)
lit_mat = kit.paint_material("leaf_lit", glow=0.85, trans=0.5)
glow_mat = kit.paint_material("leaf_glow", glow=E("GLOW", 0.8), trans=0.7, diffuse=0.4)
haze_mat = kit.paint_material("leaf_haze", glow=0.75, trans=0.5, diffuse=0.4)
core_dark = kit.emit_material("core_dark", "#1d1f18", 0.5); core_glow = kit.emit_material("core_glow", "#9a8558", 0.9)
core_right = kit.emit_material("core_right", "#8a7a5a", 0.9); core_far = kit.emit_material("core_far", "#d6c49a", 0.9)
DARK = ["#1a1c16", "#24271c", "#30341f", "#454a2c", "#5c6240"]; LIT = ["#4c5230", "#6c7440", "#8a8e52", "#b0b468", "#d4d688"]

canopy("L_canopy", [(35, 18, 8.3, 1.25), (86, 8, 8.2, 1.25), (58, 62, 8.4, 0.9), (108, 46, 8.5, 0.75), (25, -25, 9, 1.5), (100, -30, 9, 1.4), (10, 70, 7.5, 0.8), (128, 12, 8.8, 0.7)],
       DARK, dark_mat, core_dark, n=480, dab_px=9, seed=1, lit=LIT, lit_mat=lit_mat, lit_thr=E("LIT_THR", 0.16), lit_px=0.62)
canopy("L_sunny", [(152, 22, 9.8, 0.95), (186, 40, 10.4, 0.85), (140, 66, 9.6, 0.6), (172, 72, 10.2, 0.65), (206, 12, 11, 0.85), (164, -18, 10.2, 1.1), (222, 58, 11.5, 0.6)],
       ["#4a4628", "#6b6636", "#8d8648", "#b0a85e", "#d2c87c", "#efe6a6"], kit.paint_material("leaf_sunny", glow=0.7, trans=0.6, diffuse=0.5), kit.emit_material("core_sunny", "#55572f", 0.8), n=420, dab_px=8, seed=11, sunw=0.25, flat=0.33)
canopy("L_bush", [(28, 205, 5.2, 0.7), (78, 232, 5.6, 0.62), (15, 255, 4.4, 0.6), (112, 222, 7.0, 0.55), (55, 172, 7.0, 0.7), (20, 150, 6.5, 0.7), (60, 265, 4.6, 0.5)],
       DARK, dark_mat, core_dark, n=380, dab_px=10, seed=2, lit=["#3c3e26", "#555230", "#6e683a", "#8a8048"], lit_mat=lit_mat, lit_thr=0.5, lit_px=0.5, flat=0.6)
canopy("R_fol", [(492, 122, 5.0, 0.4), (503, 168, 5.2, 0.45), (482, 84, 5.4, 0.33), (508, 55, 5.0, 0.4), (452, -22, 5.2, 0.45), (497, 6, 4.8, 0.5), (510, 215, 5.5, 0.45)],
       ["#141310", "#201f19", "#2c2c20", "#3a3425", "#544939"], dark_mat, core_dark, n=380, dab_px=7, seed=3, lit=["#544939", "#7a7350", "#9a9271", "#bdb88a"], lit_mat=lit_mat, lit_thr=0.25)
canopy("R_bush", [(492, 250, 6.5, 0.55), (462, 272, 7.5, 0.45), (505, 280, 5, 0.5)], ["#221c18", "#30281f", "#3e3528", "#544a36"], dark_mat, core_dark, n=300, dab_px=8, seed=4, flat=0.6)
# back-lit glowing tree behind the left tree
canopy("M_canopy", [(162, 88, 16.5, 1.9), (202, 58, 17.5, 2.1), (232, 112, 19, 1.7), (150, 148, 15.5, 1.2), (192, 162, 16.5, 1.3), (214, 22, 19, 1.7), (142, 190, 14.5, 0.9),
                    (175, 200, 15.5, 0.9), (215, 195, 18, 1.0)],
       ["#7d6a42", "#a39160", "#c2b070", "#e0d090", "#f5e9b4", "#fff8d8"], glow_mat, core_glow, n=380, dab_px=8, seed=5, sunw=0.2)
# hazy trees on the right
canopy("R_trees", [(400, 132, 18, 1.3), (446, 122, 16.5, 1.3), (378, 165, 18.5, 1.1), (470, 158, 15.5, 1.1), (424, 170, 17, 0.9), (350, 172, 23, 1.3), (366, 205, 21, 0.8), (474, 205, 15, 0.8), (424, 100, 19, 0.8), (420, 208, 16, 0.6), (338, 205, 24, 0.9)],
       ["#6f6046", "#857355", "#9d8862", "#b3a074", "#c8b888", "#ddd0a0"], haze_mat, core_right, n=380, dab_px=8, seed=6, sunw=0.5, flat=0.36)
# far tree line beyond the clearing (what the creature hides), nearly dissolved in light
canopy("far_trees", [(248, 172, 42, 4.0), (290, 190, 46, 3.6), (332, 178, 44, 4.2), (268, 130, 52, 4.6), (312, 150, 56, 4.4), (355, 132, 60, 4.5), (220, 150, 38, 3.2), (300, 215, 34, 2.4), (255, 222, 30, 2.0)],
       ["#c2ac82", "#d4c296", "#e2d4ac", "#efe5c4"], haze_mat, core_far, n=220, dab_px=10, sub=5, seed=7, sunw=0.15)

# ferns at the lower left: arching fronds catching light
fp, fn, fc = [], [], []
for i, (px, py, d, n) in enumerate([(105, 222, 7.2, 60), (125, 200, 8.0, 50), (88, 245, 6.2, 60), (40, 235, 5.2, 50), (135, 240, 7.5, 50), (430, 250, 8.5, 50), (462, 232, 9, 40)]):
    c = np.array(kit.ground_hit(px, py + 20, H)) if False else np.array(P(px, py, d)); c[2] = H(c[0], c[1]) + 0.15
    a = rng.uniform(0, math.tau, n); rr = rng.uniform(0.05, 0.5, n)
    fp.append(c + np.stack([np.cos(a) * rr, np.sin(a) * rr, rr * 0.6], 1)); fn.append(np.stack([np.cos(a) * 2.2, np.sin(a) * 2.2, np.zeros(n)], 1))
    fc.append(pal(0.45 + 0.4 * np.cos(a - 0.3) * 0 + rng.uniform(-0.4, 0.5, n), ["#23261c", "#3c3f28", "#5e5a36", "#8e8552", "#b9ad7c"]))
kit.cards("ferns", np.concatenate(fp), np.concatenate(fn), 0.7, kit.paint_material("fern", glow=0.25, trans=0.8), seed=9, mode="blade", col=np.concatenate(fc))

# ---- sky backdrop: painted cream sky with pale cloud shapes and a glow where the sun sits; a pink peak ----
D = 150.0; sunpt = P(232, 88, D)
bm = bmesh.new(); vs = [bm.verts.new(P(px, py, D * 1.2)) for px, py in [(-150, -150), (650, -150), (650, 400), (-150, 400)]]; [setattr(v, "co", kit.CAM.location + (v.co - kit.CAM.location) * 2.2) for v in vs]; bm.faces.new(vs)
sm = bpy.data.materials.new("sky"); nt = sm.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
geo = nt.nodes.new("ShaderNodeNewGeometry"); n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.012; n1.inputs["Detail"].default_value = 2.5
nt.links.new(geo.outputs["Position"], n1.inputs["Vector"])
c = kit._ramp(nt, n1.outputs[0], [(0.0, "#fdf6e6"), (0.47, "#e6e3d3"), (0.53, "#cfd2c5"), (0.63, "#bfc0b6")])
dist = nt.nodes.new("ShaderNodeVectorMath"); dist.operation = "DISTANCE"; dist.inputs[1].default_value = P(232, 88, 240); nt.links.new(geo.outputs["Position"], dist.inputs[0])
g = kit._ramp(nt, dist.outputs["Value"], [(0.0, (1, 1, 1)), (1.0, (0, 0, 0))]); g.node.color_ramp.interpolation = "EASE"
dv = nt.nodes.new("ShaderNodeMath"); dv.operation = "DIVIDE"; dv.inputs[1].default_value = 100.0; nt.links.new(dist.outputs["Value"], dv.inputs[0]); nt.links.new(dv.outputs[0], g.node.inputs[0])
wh = nt.nodes.new("ShaderNodeRGB"); wh.outputs[0].default_value = (1.0, 0.97, 0.86, 1)
c.node.color_ramp.interpolation = "CONSTANT"; n1.inputs["Distortion"].default_value = 1.2
c = kit._mix(nt, "MIX", g, c, wh.outputs[0])
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = E("SKY_EMIT", 1.0); nt.links.new(c, em.inputs["Color"])
nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
sky = kit._obj("sky", bm, sm, smooth=False); sky.visible_shadow = False; sky.visible_diffuse = False
bm = bmesh.new(); vs = [bm.verts.new(P(px, py, D)) for px, py in [(340, 240), (348, 120), (372, 66), (396, 30), (410, 46), (428, 40), (452, 84), (480, 140), (500, 240)]]; bm.faces.new(vs)
mt = kit._obj("peak", bm, kit.emit_material("peak", "#d6b6a6", 1.0), smooth=False); mt.visible_shadow = False; mt.visible_diffuse = False
bm = bmesh.new(); vs = [bm.verts.new(P(px, py, D * 1.05)) for px, py in [(240, 240), (262, 150), (290, 110), (318, 88), (336, 100), (356, 150), (380, 240)]]; bm.faces.new(vs)
mt = kit._obj("peak2", bm, kit.emit_material("peak2", "#e9dcc8", 1.0), smooth=False); mt.visible_shadow = False; mt.visible_diffuse = False

# ---- shade pools from the unseen canopy, haze, light -----------------------------------------------
for i, (x, y, r) in enumerate([(-3.6, 7.5, 2.6), (-4.5, 11, 2.4), (-1.6, 5.5, 1.6), (4.6, 7.5, 2.2), (5.2, 11, 2.0), (-6, 14, 2.5)]):
    kit.shadow_disc(SUN, Vector((x, y, float(H(np.float64(x), np.float64(y))))), r, height=30, seed=i)
if not os.environ.get("NOFOG"):
    kit.fog(E("FOG", 0.006), (1.0, 0.86, 0.62), size=(140, E("FOG_LEN", 45), 34), at=(0, 12 + E("FOG_LEN", 45) / 2, 12), anisotropy=E("FOG_G", 0.3))
if os.environ.get("SHAFTS"): kit.shafts(SUN, [P(px, py, 17) for px, py in [(225, 150), (262, 170), (300, 160), (196, 185)]], length=30, width=(0.5, 1.4), strength=E("SHAFT", 0.012), colour=(1.0, 0.93, 0.75), seed=3)
kit.light(SUN, E("SUN_E", 5.5), (1.0, 0.9, 0.72), kit.srgb("#b8a890"), E("SKY_E", 0.35))
kit.no_specular()
kit.render(OUT, int(WIDTH), int(SAMPLES))
print("DONE")
