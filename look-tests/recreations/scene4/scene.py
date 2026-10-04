"""PROTOTYPE: recreation of owner reference scene 4 (vegetated rock pillar between cliffs), without characters."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import kit
from kit import P, cliff
OUT, WIDTH, SAMPLES = sys.argv[sys.argv.index("--") + 1:][:3]
kit.setup(500, 282, lens=40, pitch_deg=-8)

rock_far = kit.rock_material("rock_far", rock=("#737a94", "#cdc2c0", "#f8f4ec"), grass=("#a9cdb0", "#c4e2c4"), grass_from=0.8, patch="#c79a94", moss="#84cc9a", patch_scale=0.005)
rock_midl = kit.rock_material("rock_midl", rock=("#22383c", "#3e575b", "#5e787c"), grass=("#2f5f3a", "#4f8050"), grass_from=0.8, patch="#8a8a88", moss="#2f5a42", patch_scale=0.03)
rock_left = kit.rock_material("rock_left", rock=("#857a66", "#aaa08a", "#cdc5b0"), grass=("#4f8f48", "#7fb860"), grass_from=0.75, patch="#b8a890", patch_scale=0.07, tilt=0.6, streak=1.5, zscale=0.02)
rock_under = kit.rock_material("rock_under", rock=("#5a5044", "#7a6e5e", "#958a76"), grass_from=2.0)
rock_pillar = kit.rock_material("rock_pillar", rock=("#6f5f48", "#a3906f", "#cbbd9c"), grass=("#3f7f40", "#6aa858"), grass_from=0.7, streak=1.6, zscale=0.006)
rock_rback = kit.rock_material("rock_rback", rock=("#172222", "#2c3c40", "#465a5e"), grass=("#28502c", "#3a6a38"), grass_from=0.8, moss="#1f4026", patch_scale=0.03)
rock_rnear = kit.rock_material("rock_rnear", rock=("#161d1f", "#2a3536", "#404d4f"), grass=("#356a30", "#5a9644"), grass_from=0.72, patch="#5a6880", moss="#1c3622", patch_scale=0.05)

core_b = kit.flat_material("core_b", "#1c4a22"); core_m = kit.flat_material("core_m", "#2f5a3a"); core_l = kit.flat_material("core_l", "#5a8458")
leaf_right = kit.leaf_material("leaf_right", "#17401f", "#35852f", "#74c44a", "#bcec78", glow=0.18)
leaf_rdark = kit.leaf_material("leaf_rdark", "#12301c", "#1f4a28", "#2f6432", "#4a8040", glow=0.04)
leaf_pillar = kit.leaf_material("leaf_pillar", "#3c7448", "#5c9e62", "#82c472", "#b8e69a", glow=0.22)
leaf_left = kit.leaf_material("leaf_left", "#5c9058", "#7ab468", "#9cd07a", "#c8eaa0", glow=0.22)

# far pale wall
cliff("far", [(-60, -60, 950), (60, -70, 900), (160, -60, 880), (260, -70, 900), (360, -60, 880), (560, -60, 900)],
      [(-60, 340, 950), (60, 340, 900), (160, 340, 880), (260, 340, 900), (360, 340, 880), (560, 340, 900)], rock_far, back=200, rough=1.5, seed=1)
# mid-left blue-grey cliff, behind the leaning one
cliff("midl", [(20, -40, 180), (80, -40, 185), (128, -40, 190), (146, -40, 215), (152, -40, 280)],
      [(20, 320, 180), (90, 320, 185), (150, 320, 190), (172, 320, 215), (178, 320, 280)], rock_midl, back=60, rough=1.2, seed=2)
# near-left leaning tan cliff: face, then its underside
cliff("left", [(-70, 200, 55), (-70, -70, 60), (60, -70, 68), (185, -70, 84)],
      [(-25, 190, 60), (30, 152, 63), (62, 118, 66), (108, 58, 74), (162, -20, 84)], rock_left, back=20, rough=0.7, seed=3)
cliff("left_under", [(-25, 190, 61), (30, 152, 64), (62, 118, 67), (108, 58, 75), (162, -20, 85)],
      [(-13, 199, 85), (42, 160, 88), (74, 126, 92), (120, 64, 100), (175, -15, 110)], rock_under, back=1, rough=0.5, seed=4)
# right: back mass (dark), and the near ledge with trees
cliff("rback", [(308, -40, 230), (318, -40, 175), (345, -40, 155), (420, -40, 150), (540, -40, 150)],
      [(330, 320, 230), (338, 320, 175), (355, 320, 155), (420, 320, 150), (540, 320, 150)], rock_rback, back=40, rough=1.1, seed=5)
cliff("rnear", [(356, 101, 76), (400, 88, 68), (450, 72, 60), (520, 50, 52)],
      [(404, 135, 82), (440, 175, 72), (474, 232, 64), (530, 310, 56)], rock_rnear, back=40, rise=2, rough=0.8, seed=6)

# the pillar
PD = 220
kit.pillar("pillar", [(208, 22, PD, 17), (207, 60, PD, 17), (205, 110, PD, 16), (203, 160, PD, 16), (203, 210, PD, 15), (202, 300, PD, 17)], rock_pillar, seed=7)
F = PD - 7
kit.clumps("pil", [(208, 26, PD, 8.5, 0.6), (195, 36, F, 5.5), (221, 32, F, 4.5), (193, 54, F, 4.6, 1.3), (191, 74, F, 4.2, 1.4), (203, 80, F, 3.6), (216, 72, F, 3.0),
                   (193, 94, F, 3.8), (196, 108, F, 2.8), (221, 116, F, 2.0), (190, 128, F, 2.2, 1.5), (177, 150, F, 5.4), (186, 162, F, 4.0), (222, 162, F, 2.0),
                   (210, 180, F, 4.2), (215, 193, F, 3.4), (188, 196, F, 3.2), (206, 214, F, 4.0), (213, 225, F, 3.2), (180, 232, F, 4.6), (185, 248, F, 4.0),
                   (213, 247, F, 2.6), (196, 258, F, 4.2), (188, 270, F, 4.8), (208, 274, F, 3.4)], core_m, leaf_pillar, seed=20, lumps=45, leaves=100, leaf=0.085)

# trees on the right ledge
kit.clumps("rtree", [(440, 0, 84, 8), (385, 38, 84, 4.5), (402, 24, 82, 4.2), (420, 14, 80, 4.6), (445, 22, 74, 4.4), (466, 12, 70, 4.6), (490, 16, 64, 4.4), (396, 52, 78, 3.6), (418, 42, 76, 3.8), (438, 46, 72, 3.4),
                     (460, 38, 66, 3.6), (482, 40, 60, 3.4), (370, 62, 82, 3.2), (386, 70, 78, 2.8), (408, 68, 74, 3.0), (430, 64, 70, 2.8), (452, 58, 64, 2.8), (474, 54, 58, 2.6), (364, 84, 80, 2.2), (378, 86, 77, 1.8), (496, 44, 54, 2.6)],
           core_b, leaf_right, seed=50, lumps=45, leaves=110, leaf=0.085, lump=(0.2, 0.36), squash=0.7)
# dark growth on the right back mass
kit.clumps("rdark", [(325, 12, 150, 7), (336, 35, 148, 7), (345, 60, 146, 6), (330, 150, 150, 5), (340, 190, 148, 5), (360, 130, 144, 5), (450, 200, 110, 5), (468, 240, 100, 5), (480, 268, 80, 4)],
           core_b, leaf_rdark, seed=70, lumps=40, leaves=70, leaf=0.1)
# growth on the left cliff
import random
rnd = random.Random(3)
lf = [(12, 14), (30, 8), (48, 14), (66, 10), (84, 22), (100, 12), (20, 32), (40, 28), (62, 40), (78, 34), (96, 40), (112, 26), (122, 12), (6, 84), (14, 100), (4, 66), (46, 104), (52, 122), (55, 132), (62, 142), (14, 150), (30, 156), (42, 150), (30, 62), (8, 44), (132, 4), (56, 2), (90, 2)]
kit.clumps("lfol", [(x, y, 50 + x * 0.14, rnd.uniform(0.9, 1.7), 0.55) for x, y in lf], core_l, leaf_left, seed=90, lumps=40, leaves=80, leaf=0.11)
kit.clumps("mfol", [(122, 62, 172, 6), (130, 36, 176, 6), (118, 92, 170, 5), (136, 100, 176, 4), (125, 195, 170, 6), (152, 215, 176, 5), (146, 250, 172, 6), (142, 132, 178, 4), (100, 160, 168, 5), (128, 150, 170, 4), (150, 172, 180, 4)], core_m, leaf_rdark, seed=110, lumps=30, leaves=60, leaf=0.12)

# clouds: (px, py, d, radius, stretch, squash)
for i, (px, py, d, r, st, sq) in enumerate([(30, 212, 120, 8, 1.5, 0.75), (72, 240, 115, 7, 1.5, 0.75), (14, 262, 100, 7, 1.5, 0.7), (100, 270, 112, 6, 1.6, 0.6), (50, 180, 125, 5, 1.6, 0.6),
                                            (98, 136, 200, 4.5, 2.4, 0.4), (88, 112, 210, 3, 3.0, 0.25),
                                            (405, 228, 115, 5, 2.4, 0.5), (455, 240, 105, 4, 2.2, 0.5), (365, 250, 125, 4.5, 2.4, 0.5), (420, 268, 100, 4.5, 2.4, 0.5),
                                            (250, 284, 150, 6, 2.6, 0.45), (160, 284, 135, 6, 2.2, 0.5), (320, 280, 140, 5, 2.4, 0.5), (285, 160, 640, 22, 3.0, 0.3)]):
    kit.cloud("cloud", P(px, py, d), r * 1.15, seed=80 + i, stretch=st, squash=sq, density=0.55, emit=0.5, wisp=0.4, edge=0.6)

SUN = (-0.7, 0.1, -0.7)
kit.fog(0.0011, (0.9, 0.96, 0.97), size=(2400, 1800, 1400), at=(0, 165 + 900, -200))
kit.shafts(SUN, [P(px, py, 420) for px, py in [(255, 70), (285, 40), (310, 100), (330, 60), (270, 130), (240, 20)]], length=700, width=(8, 22), strength=0.00045, seed=3)
kit.light(SUN, 8.0, (1.0, 0.96, 0.86), (0.78, 0.88, 0.93), 1.3)
kit.render(OUT, int(WIDTH), int(SAMPLES))
print("DONE")
