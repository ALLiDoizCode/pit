"""PROTOTYPE: recreation of owner reference scene 8 (high view over a forested basin with a hole), without characters."""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import kit
from kit import P, Z, cliff
from mathutils import Vector
OUT, WIDTH, SAMPLES = sys.argv[sys.argv.index("--") + 1:][:3]
kit.setup(500, 281, lens=28, pitch_deg=-36)
FLOOR = -600.0
F = lambda px, py, h=0.0: Z(px, py, FLOOR + h)

# ---- basin floor with the hole -----------------------------------------------------------
canopy = kit.canopy_material("canopy", light="#528e66", dark="#2a705c", wall_dark="#18393a", wall_light="#3f8258", pit="#2a1426",
                             r_in=160, r_out=295, z_pit=-36)
kit.basin_floor("floor", F(247, 146), canopy, r_pit=118, r_funnel=230, seed=3)

# ---- far cliffs ---------------------------------------------------------------------------
rock_far = kit.rock_material("rock_far", rock=("#6a6f74", "#9a9fa3", "#cfd0cf"), grass=("#5fa070", "#8fcf90"), grass_from=0.9, patch="#c9c4bc", moss="#6f9a7c", patch_scale=0.004, streak=0.25)
def wall(name, base_px, height, lean=0.12, seed=0, mat=None, **kw):
    base = [F(px, py) for px, py in base_px]; lip = []
    for b in base:
        away = Vector((b.x, b.y, 0)).normalized(); lip.append(b + away * height * lean + Vector((0, 0, height)))
    return cliff(name, lip, base, mat or rock_far, seed=seed, strata=0.0, **kw)
wall("cliff_top", [(95, 44), (140, 37), (200, 36), (260, 34), (330, 27), (420, 22), (540, 26)], 620, back=400, rough=0.35, seed=1)
rock_left = kit.rock_material("rock_left", rock=("#868c90", "#b0b6b9", "#dcdede"), grass=("#6fb07c", "#9ad79a"), grass_from=0.8, patch="#d8d4cc", moss="#86b090", patch_scale=0.004, streak=0.25)
wall("cliff_left", [(-40, 150), (-5, 124), (25, 96), (50, 78), (72, 64), (100, 50)], 300, back=500, rough=0.4, seed=2, mat=rock_left)

# ---- near hills ---------------------------------------------------------------------------
grass_r = kit.grass_material("grass_r", "#4a9a4c", "#64ba56", "#80d462", scale=0.12)
grass_dark = kit.grass_material("grass_dark", "#081614", "#0c201d", "#122c27", scale=0.1)
def hill(name, lip_px, d_lip, d_base, mat, **kw):
    return cliff(name, [(x, y, d_lip) for x, y in lip_px], [(x, 430, d_base) for x, y in lip_px], mat, **kw)
hill_r = hill("hill_right", [(280, 284), (310, 268), (340, 257), (375, 251), (410, 247), (438, 230), (456, 206), (470, 186), (486, 177), (510, 172)], 55, 22, grass_r, back=8, rise=-6, rough=0.25, seed=5)
hill_l = hill("hill_left", [(-20, 196), (40, 213), (90, 232), (140, 250), (200, 263), (260, 270), (310, 280)], 110, 40, grass_dark, back=10, rise=-8, rough=0.3, seed=6)

tuft_m = kit.tuft_material("tuft", ["#5aac50", "#6abc56", "#7acc5e", "#8edc68"])
kit.tufts("tufts_r", hill_r, tuft_m, count=40000, size=0.16, seed=3).visible_shadow = False
core_b = kit.flat_material("core_b", "#1c3a2a"); leaf_b = kit.leaf_material("leaf_b", "#1f4a30", "#357a40", "#58a04c", "#80c060", glow=0.03)
kit.foliage("bush", P(401, 240, 52), 1.6, core_b, leaf_b, lumps=30, leaves=70, leaf=0.1, seed=4)
# waterfalls on the far left cliff
kit.strip("fall1", F(38, 30, 290), F(44, 82, 10), 1.2, 2.5, emit=0.28)
kit.strip("fall2", F(84, 14, 420), F(88, 60, 10), 1.2, 2.2, emit=0.2)

# mid-distance ledge at the left
rock_mid = kit.rock_material("rock_mid", rock=("#3c5048", "#5c7468", "#84988a"), grass=("#4a9058", "#58a264"), grass_from=0.7, moss="#3f7a52", patch_scale=0.03)
ZL = -300.0
kit.mesa("ledge", [Z(px, py, ZL) for px, py in [(58, 160), (92, 166), (89, 190), (100, 212), (60, 214), (30, 200), (22, 180)]], 80, rock_mid, flare=0.35, rough=5, seed=7)
slope = kit.grass_material("slope", "#1f5038", "#2a6444", "#357650", scale=0.03)
sl = hill("slope_l", [(-30, 146), (20, 150), (52, 158), (66, 178), (74, 205), (84, 235), (100, 260)], 470, 160, slope, back=30, rise=-10, rough=0.25, seed=8)

sl.data.set_sharp_from_angle(angle=math.radians(180))
# dark trees on the near left hill
core_d = kit.flat_material("core_d", "#0c211f"); leaf_d = kit.leaf_material("leaf_d", "#0c2220", "#143430", "#1d4a40", "#2a6050", glow=0.02)
for i, (px, py, d, r) in enumerate([(8, 246, 60, 6), (30, 262, 55, 5), (-5, 272, 50, 5), (140, 272, 50, 3.2), (160, 280, 48, 2.6), (120, 281, 48, 2.2)]):
    kit.foliage("tree_d", P(px, py, d), r, core_d, leaf_d, lumps=60, leaves=110, leaf=0.045, seed=20 + i)

# ---- clouds -------------------------------------------------------------------------------
CLOUD_H = 150.0
PXM = 2 * (18 / 28) / 500          # metres per pixel per metre of distance
clouds = [(95, 2, 22), (180, -2, 22), (152, 42, 40), (238, 20, 20), (315, 62, 42), (370, 4, 26), (455, 25, 52), (458, 118, 58),
          (328, 156, 28), (28, 122, 40), (160, 212, 68), (335, 236, 42), (400, 202, 52), (452, 172, 34)]
for i, (px, py, rpx) in enumerate(clouds):
    c = F(px, py, CLOUD_H); r = rpx * c.length * PXM
    kit.cloud("cloud", c, r / 1.6, density=3.2, seed=60 + i, squash=0.4, stretch=1.7, wisp=0.5, n=60, lump=(0.2, 0.42), emit=0.13, nscale=5.0, bumpy=0.5, emit_colour=(1.0, 0.9, 1.0))

# ---- light ---------------------------------------------------------------------------------
SUN = (-0.3, 0.25, -1.0)
kit.fog(0.0002, (0.86, 0.84, 1.0), size=(8000, 8000, 760), at=(0, 2000, -280))
kit.light(SUN, 3.4, (1.0, 0.95, 0.92), (0.6, 0.72, 0.98), 0.9)
kit.render(OUT, int(WIDTH), int(SAMPLES))
print("DONE")
