"""PROTOTYPE: recreation of owner reference scene 1 (cliff ledge above a cloud sea), without characters."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import kit
from kit import P, cliff, puff
from mathutils import Vector
OUT, WIDTH, SAMPLES = sys.argv[sys.argv.index("--") + 1:][:3]
kit.setup(500, 281, lens=40, pitch_deg=-14)

rock_near = kit.rock_material("rock_near", rock=("#141214", "#2c2828", "#4f4744"), grass=("#3c9a22", "#8ee03a"), patch="#8a7868", moss="#2c5a26", patch_scale=0.06)
rock_mid = kit.rock_material("rock_mid", rock=("#1c2a2a", "#3a4a48", "#6f7068"), grass=("#1f5f2a", "#3f8f3a"), grass_from=0.78, patch="#c79a8a", moss="#24553a", patch_scale=0.018)
rock_far = kit.rock_material("rock_far", rock=("#5d6a6c", "#839290", "#b9bdb2"), grass=("#5f8a68", "#7fa98a"), grass_from=0.8, patch="#d8cfc0", moss="#5a8a6a", patch_scale=0.008)
core_near, core_mid = kit.flat_material("core_near", "#0d3018"), kit.flat_material("core_mid", "#12382a")
leaf_near = kit.leaf_material("leaf_near", "#12451d", "#2c9226", "#74d835", "#c6f26a")
leaf_mid = kit.leaf_material("leaf_mid", "#17472f", "#2a7f38", "#58b146", "#98d86c", glow=0.06)

# far, hazy cliffs with a waterfall (upper left) and the lit cliff at upper right
cliff("far_left", [(-20, 12, 900), (60, -2, 900), (110, 8, 880), (170, 28, 860), (240, 22, 840), (300, 40, 820)],
      [(-20, 190, 900), (60, 190, 900), (110, 190, 880), (170, 190, 860), (240, 190, 840), (300, 190, 820)], rock_far, back=200, rough=0.8, seed=1)
cliff("far_right", [(330, 22, 420), (380, 4, 410), (430, -6, 400), (520, -10, 390)],
      [(330, 150, 420), (380, 150, 410), (430, 150, 400), (520, 150, 390)], rock_far, back=120, rough=1.0, seed=2)
# the broad middle plateau
cliff("mid", [(-30, 100, 300), (30, 84, 300), (90, 88, 295), (140, 62, 290), (178, 46, 288), (212, 52, 284), (252, 74, 280), (300, 98, 274), (345, 116, 268)],
      [(-30, 250, 300), (30, 250, 300), (90, 250, 295), (140, 250, 290), (178, 250, 288), (212, 250, 284), (252, 250, 280), (300, 250, 274), (345, 250, 268)],
      rock_mid, back=45, rise=-4, rough=2.0, seed=3)
# the near promontory we look across at, undercut toward its tip
cliff("near", [(262, 182, 78), (292, 172, 75), (332, 160, 70), (382, 148, 64), (442, 133, 58), (520, 114, 50)],
      [(372, 330, 80), (402, 330, 77), (432, 330, 72), (462, 330, 66), (492, 330, 60), (540, 330, 52)], rock_near, back=26, rise=2, rough=1.0, seed=4)

# foliage: the big tree masses on the promontory, and clumps on the plateau
for i, (px, py, d, r) in enumerate([(402, 78, 86, 11.5), (468, 96, 76, 8.5), (340, 118, 86, 5.0), (300, 146, 84, 2.2), (488, 190, 62, 3.2), (470, 262, 66, 3.0), (352, 262, 82, 2.6)]):
    kit.foliage("tree_near", P(px, py, d), r, core_near, leaf_near, lumps=70, leaves=120, leaf=0.05 if r > 4 else 0.09, seed=10 + i, lump=(0.18, 0.32))
for i, (px, py, d, r) in enumerate([(55, 168, 286, 20), (28, 190, 284, 12), (72, 140, 290, 10), (180, 100, 296, 9), (150, 84, 300, 12), (118, 74, 304, 9), (96, 150, 290, 8), (230, 86, 292, 7), (40, 96, 306, 10), (300, 110, 280, 6), (210, 152, 282, 6)]):
    kit.foliage("clump_mid", P(px, py, d), r, core_mid, leaf_mid, lumps=40, leaves=60, leaf=0.11, seed=40 + i, lump=(0.2, 0.36))

# waterfall on the far cliff
import bmesh, bpy
wf = bmesh.new(); a, b = P(100, -4, 640), P(104, 92, 640)
vs = [wf.verts.new(a + Vector((-1.5, 0, 0))), wf.verts.new(a + Vector((1.5, 0, 0))), wf.verts.new(b + Vector((4, 0, 0))), wf.verts.new(b + Vector((-4, 0, 0)))]; wf.faces.new(vs)
wm = bpy.data.materials.new("water"); wb = wm.node_tree.nodes["Principled BSDF"]; wb.inputs["Base Color"].default_value = (0.9, 0.95, 1, 1); wb.inputs["Emission Color"].default_value = (0.9, 0.95, 1, 1); wb.inputs["Emission Strength"].default_value = 1.2
kit._obj("waterfall", wf, wm, smooth=False)

# the cloud sea, below everything
import random
rnd = random.Random(5)
for i, (px, py, d, r) in enumerate([(110, 232, 240, 30), (30, 250, 210, 28), (200, 262, 200, 24), (150, 276, 160, 22), (40, 214, 330, 30), (250, 228, 250, 18), (300, 262, 180, 16), (10, 176, 440, 30), (90, 292, 130, 20), (235, 296, 145, 18), (180, 230, 300, 20), (330, 240, 250, 16), (-10, 285, 150, 22)]):
    kit.cloud("cloud", P(px, py, d), r * 1.3, seed=80 + i)

SUN = (-0.72, -0.3, -0.62)
kit.fog(0.0008, (0.72, 0.9, 1.0))
kit.shafts(SUN, [P(px, py, 215) for px, py in [(150, 70), (205, 60), (250, 80), (300, 60), (118, 110), (345, 95)]], seed=3)
kit.light(SUN, 9.0, (1.0, 0.95, 0.82), (0.42, 0.66, 0.86), 0.8)
kit.render(OUT, int(WIDTH), int(SAMPLES))
print("DONE")
