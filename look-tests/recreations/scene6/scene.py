"""PROTOTYPE: recreation of owner reference scene 6 (town around the mouth of a giant pit), without characters."""
import sys, math, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import kit
import numpy as np
from kit import P, Z, cliff, srgb
from mathutils import Vector, noise
OUT, WIDTH, SAMPLES = sys.argv[sys.argv.index("--") + 1:][:3]
kit.setup(500, 282, lens=32.4, pitch_deg=-14)
RIM = -1000.0
far, near = Z(250, 104, RIM), Z(250, 241, RIM)
C = (far + near) / 2; R = (far - near).length / 2
print("pit centre", C, "radius", R)
OFF = Vector((3.1, 7.7, 1.3))
ridged = lambda p: 1 - 2 * abs(noise.noise(p))

def rim_r(th):
    u = Vector((math.cos(th), math.sin(th), 0))
    return R * (1 + 0.035 * noise.noise(u * 2.3 + OFF) + 0.014 * noise.noise(u * 8 + OFF * 2) + 0.006 * noise.noise(u * 25 + OFF))

def mount(x, y, s):
    return max(0.0, min(1.0, (s - 2300 + 0.5 * max(0.0, abs(x - C.x) - 2600) + 500 * noise.noise(Vector((x, y, 0)) * 0.0006 + OFF)) / 1300))

def ground_s(x, y, s):
    p = Vector((x, y, 0)); m = mount(x, y, s)
    z = RIM + 0.10 * s + 0.00006 * s * s + 14 * noise.noise(p * 0.004 + OFF) * min(1.0, s / 150) + 60 * noise.noise(p * 0.0011) * min(1.0, s / 600)
    z += m * (260 * ridged(p * 0.0011 + OFF) + 90 * ridged(p * 0.0034) + 45 * noise.noise(p * 0.01) + 250 * m)
    return z, m

def ground(x, y):
    dx, dy = x - C.x, y - C.y; th = math.atan2(dy, dx); s = math.hypot(dx, dy) - rim_r(th)
    return ground_s(x, y, s)

# ---- terrain ring + inner wall as one mesh ------------------------------------------------
SEG = 900
ths = [math.tau * k / SEG for k in range(SEG)]; rr = [rim_r(t) for t in ths]
svals = [0.0]; 
while svals[-1] < 9000: svals.append(svals[-1] + 10 + svals[-1] * 0.035)
rows, cols = [], []
G1, G2 = np.array(srgb("#23281a")), np.array(srgb("#3b3d26")); RK1, RK2, RK3 = np.array(srgb("#857a60")), np.array(srgb("#c4b48c")), np.array(srgb("#e6dcb8"))
for s in reversed(svals):
    row, col = [], []
    for t, r0 in zip(ths, rr):
        x, y = C.x + math.cos(t) * (r0 + s), C.y + math.sin(t) * (r0 + s); z, m = ground_s(x, y, s)
        row.append((x, y, z)); g = 0.5 + 0.5 * noise.noise(Vector((x, y, 0)) * 0.003)
        k = 0.5 + 0.5 * noise.noise(Vector((x * 0.004, y * 0.004, z * 0.012)))
        rock = RK1 + (RK2 - RK1) * min(1, k * 1.6) if k < 0.62 else RK2 + (RK3 - RK2) * (k - 0.62) / 0.38
        col.append((G1 + (G2 - G1) * g) * (1 - m) + rock * m)
    rows.append(row); cols.append(col)
W1, W2 = np.array(srgb("#1c1f2c")), np.array(srgb("#3c4052"))
for d in [8, 30, 70, 130, 210, 320, 460, 640, 880, 1200, 1600, 2100, 2800, 3600]:
    row, col = [], []
    for t, r0 in zip(ths, rr):
        u = Vector((math.cos(t), math.sin(t), 0))
        inset = 0.05 * d + 22 * min(1.0, d / 60) * (ridged(u * 14 + Vector((0, 0, d * 0.0012))) + 0.5 * ridged(u * 40 + Vector((0, 0, d * 0.003)) + OFF))
        r = r0 - inset; row.append((C.x + u.x * r, C.y + u.y * r, RIM - d))
        k = 0.5 + 0.5 * noise.noise(u * 30 + Vector((0, 0, d * 0.002)))
        col.append((W1 + (W2 - W1) * k) * max(0.25, 1 - d / 2600) + np.array([0.03, 0.028, 0.026]) * max(0.0, 1 - d / 250))
    rows.append(row); cols.append(col)
rows.append([(C.x + math.cos(t) * 5, C.y + math.sin(t) * 5, RIM - 3700) for t in ths]); cols.append([W1 * 0.2] * SEG)
terr_mat = kit.attr_material("terrain", emit=0.02, mottle=0.35, mottle_scale=0.02)
terr = kit.grid_mesh("terrain", rows, cols, terr_mat)
terr.data.set_sharp_from_angle(angle=math.radians(40))

# ---- the town: one numpy mesh ---------------------------------------------------------------
rng = np.random.default_rng(6)
M = 1400000; S_MAX = 4200
th = rng.uniform(0, math.tau, M); r = np.sqrt(rng.uniform(R * R, (R + S_MAX) ** 2, M))
x, y = C.x + r * np.cos(th), C.y + r * np.sin(th); s = r - R
z0 = RIM + 0.10 * s + 0.00006 * s * s
pts = np.stack([x, y, z0], 1); u, v, depth = kit.project(pts); dist = np.linalg.norm(pts, axis=1)
size = 21.0 * (dist / 1800.0) ** 0.85
ok = (depth > 0) & (u > -20) & (u < 520) & (v > -10) & (v < 300) & (rng.uniform(0, 1, M) < 0.75 * (21.0 / size) ** 2 * 0.5)
idx = np.nonzero(ok)[0]; pos, keep = [], []
for i in idx:
    dx, dy = x[i] - C.x, y[i] - C.y; t = math.atan2(dy, dx); ss = math.hypot(dx, dy) - rim_r(t)
    if ss < 6: continue
    z, m = ground_s(x[i], y[i], ss)
    if m > 0.02 and random.random() < m * 4: continue
    # patchy density: leave green gaps
    if noise.noise(Vector((x[i], y[i], 0)) * 0.0035 + OFF) < -0.33: 
        if random.random() < 0.7: continue
    pos.append((x[i], y[i], z)); keep.append(i)
pos = np.array(pos); keep = np.array(keep); N = len(pos); print("buildings", N)
sz = size[keep]; tree = rng.uniform(0, 1, N) < 0.5
w = sz * rng.uniform(0.55, 1.25, N); d = sz * rng.uniform(0.7, 2.0, N); h = sz * rng.uniform(0.3, 0.85, N); rh = sz * rng.uniform(0.2, 0.5, N)
w[tree] = d[tree] = sz[tree] * rng.uniform(0.6, 1.1, tree.sum()); h[tree] = sz[tree] * 0.25; rh[tree] = sz[tree] * rng.uniform(0.6, 1.1, tree.sum())
field = np.array([noise.noise(Vector((p[0], p[1], 0)) * 0.002) for p in pos]) * 3.0
yaw = field + rng.normal(0, 0.25, N) + rng.integers(0, 2, N) * math.pi / 2
ROOFS = ["#c9b45a", "#d8c878", "#c88a3c", "#b0622c", "#8a5a34", "#e2d8b0", "#f0ead2", "#7c8448", "#9a9a5c", "#5a5236", "#a84a2a", "#b8a070", "#6a7a50", "#d6a850"]
WALLS = ["#d8d0b4", "#b8ac8c", "#8a8068", "#e8e2cc", "#6e6650", "#a09070"]
TREES = ["#1e3014", "#2c4218", "#3a541c", "#4c6624", "#283c1a", "#5a7028"]
pal = lambda names: np.array([srgb(c) for c in names])
rc = pal(ROOFS)[rng.integers(0, len(ROOFS), N)]; wc = pal(WALLS)[rng.integers(0, len(WALLS), N)]
tc = pal(TREES)[rng.integers(0, len(TREES), N)]; rc[tree] = tc[tree]; wc[tree] = tc[tree] * 0.7
rc = (rc * 0.62 + rc.mean(1, keepdims=True) * 0.38) * rng.uniform(0.45, 0.9, (N, 1)) * np.array([1.0, 0.98, 0.86]); wc *= 0.55
town_mat = kit.attr_material("town", emit=0.03)
kit.buildings("town", pos, yaw, np.stack([w, d, h], 1), rh, rc, wc, town_mat)

# ---- structures hanging down the inner wall ---------------------------------------------------
NW = 9000
tw = rng.uniform(0, math.tau, NW); dw = rng.exponential(90, NW) + 30
pw, yw = [], []
keepw = np.array([noise.noise(Vector((math.cos(t) * 6, math.sin(t) * 6, dd * 0.01))) > 0.05 for t, dd in zip(tw, dw)]); tw, dw = tw[keepw], dw[keepw]; NW = len(tw)
for t, dd in zip(tw, dw):
    r0 = rim_r(t) - 0.05 * dd - 5; pw.append((C.x + math.cos(t) * r0, C.y + math.sin(t) * r0, RIM - dd)); yw.append(t + math.pi / 2)
pw = np.array(pw); ww = rng.uniform(12, 40, NW); dd2 = rng.uniform(20, 45, NW); hw = np.minimum(rng.uniform(6, 30, NW) * np.where(rng.uniform(0, 1, NW) < 0.15, 3, 1), dw - 8)
WC = pal(["#6a5a48", "#8a7860", "#544a3e", "#9a8a6a", "#3e3a36", "#7a6a50", "#b0a080"]) * 0.7
kit.buildings("wall_town", pw, np.array(yw), np.stack([ww, dd2, hw], 1), rng.uniform(2, 6, NW), WC[rng.integers(0, len(WC), NW)], WC[rng.integers(0, len(WC), NW)] * 0.8, town_mat)

# ---- waterfalls down the far wall ---------------------------------------------------------------
for i, (px, py, L, wd) in enumerate([(60, 134, 500, 7), (87, 123, 600, 7), (115, 117, 1500, 8), (187, 106, 1400, 8), (207, 104, 1200, 7), (323, 105, 1400, 8), (372, 108, 1400, 8), (430, 128, 500, 7), (282, 104, 500, 5), (150, 110, 400, 5)]):
    a = Z(px, py, RIM - 4); a = a + (C - a).normalized() * 75; a.z = RIM - 4
    kit.strip("fall%d" % i, a, a + Vector((0, 0, -L)), wd * 0.45, wd * 0.9, colour=(0.75, 0.8, 0.95), emit=0.12)

# ---- clouds in the pit -----------------------------------------------------------------------------
kit.cloud_layer("clouds", (C.x, C.y, RIM - 170), R * 0.97, 130, cover=0.515, density=0.016, scale=1300, stretch=(1.0, 0.45, 1.0), emit=0.006, seed=2.0)
kit.cloud_layer("clouds2", (C.x, C.y, RIM - 360), R * 0.95, 160, cover=0.53, density=0.014, scale=1000, stretch=(1.0, 0.45, 1.0), emit=0.005, seed=9.0)

# ---- foreground outcrops ---------------------------------------------------------------------------
grass_f = kit.grass_material("grass_f", "#7c7c46", "#a09a5c", "#c2b878", scale=0.02, bump=0.5)
def hill(name, lip_px, d_lip, d_base, mat, **kw):
    return cliff(name, [(x, y, d_lip) for x, y in lip_px], [(x, 460, d_base) for x, y in lip_px], mat, **kw)
hill("hill_l", [(-30, 218), (0, 224), (20, 232), (45, 248), (70, 264), (95, 276), (125, 292)], 520, 380, grass_f, back=60, rise=-30, rough=0.25, seed=5, strata=0)
hill("hill_r", [(385, 292), (410, 277), (435, 268), (462, 259), (485, 250), (530, 240)], 520, 380, grass_f, back=60, rise=-30, rough=0.25, seed=6, strata=0)

# ---- light -----------------------------------------------------------------------------------------
SUN = (0.62, -0.42, -0.66)
kit.haze(0.00011, (1.0, 0.92, 0.76), size=(40000, 16000, 3200), at=(0, C.y + R + 200 + 8000, RIM + 1600), scatter=0.00003)
kit.haze(0.000016, (0.62, 0.66, 0.85), size=(44000, 30000, 7000), at=(0, 14000, RIM - 1500))
kit.light(SUN, 4.5, (1.0, 0.95, 0.86), (0.8, 0.84, 0.95), 0.9)
kit.no_specular()
kit.render(OUT, int(WIDTH), int(SAMPLES))
print("DONE")
