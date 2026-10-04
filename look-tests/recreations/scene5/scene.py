"""PROTOTYPE: recreation of owner reference scene 5 (misty layered ledges), without characters."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import kit
from kit import P, H, cliff
OUT, WIDTH, SAMPLES = sys.argv[sys.argv.index("--") + 1:][:3]
kit.setup(500, 281, lens=35, pitch_deg=-2)

def base(lip, py=340): return [(x, py, d) for x, _, d in lip]
def flat(pts, d): return [(x, y, d) for x, y in pts]

far_m = kit.rock_material("far", rock=("#6c7e8e", "#788a98", "#8496a2"), grass=("#788a98", "#8496a2"), grass_from=0.9)
mid_m = kit.rock_material("mid", rock=("#364c68", "#445c78", "#526a84"), grass=("#445c78", "#587088"), grass_from=0.8)
midr_m = kit.rock_material("midr", rock=("#34465a", "#43566a", "#526478"), grass=("#43566a", "#526478"), grass_from=0.8)
plat_m = kit.rock_material("plat", rock=("#27444a", "#33575a", "#3f6866"), grass=("#356658", "#5c9670"), grass_from=0.9, grass_scale=0.012, moss="#3c6658", patch_scale=0.01)
pill_m = kit.rock_material("pill", rock=("#27434a", "#33555a", "#3f6866"), grass=("#3f7458", "#5c9068"), grass_from=0.78, moss="#3a665c", patch_scale=0.02, grass_scale=0.05)
dark_m = kit.rock_material("dark", rock=("#263f44", "#30505a", "#3d6266"), grass=("#3f6a5c", "#5a8a70"), grass_from=0.8, grass_scale=0.03, moss="#35605a", patch_scale=0.02)
core_g, core_d = kit.flat_material("core_g", "#2a4c48"), kit.flat_material("core_d", "#1e3238")
leaf_g = kit.leaf_material("leaf_g", "#3c6a5a", "#4c8262", "#5e966a", "#74a876", glow=0.08)
leaf_d = kit.leaf_material("leaf_d", "#1f363e", "#2a4a50", "#38605e", "#4a7868", glow=0.03)
sil_m = kit.emit_material("sil", "#5d6a78", vary=0.06, scale=0.4)

# far mesas on the horizon, then the blue-grey middle ridges
cliff("far", flat([(-20, 118), (60, 120), (118, 114), (138, 104), (190, 100), (240, 103), (256, 115), (300, 121), (344, 118), (360, 106), (420, 104), (480, 108), (520, 112)], 2400),
      flat([(-20, 170), (520, 170)], 2400), far_m, back=300, rough=0.15, seed=1, jag=0.15)
cliff("mid_l", flat([(-20, 138), (60, 131), (120, 140), (160, 146), (200, 142), (240, 136), (290, 145), (330, 140), (390, 150)], 1000),
      flat([(-20, 210), (390, 210)], 1000), mid_m, back=300, rough=0.3, seed=2, jag=0.5)
cliff("mid_c", flat([(180, 160), (215, 152), (250, 154), (300, 160), (340, 158), (400, 165)], 880),
      flat([(180, 215), (400, 215)], 880), mid_m, back=200, rough=0.35, seed=5, jag=0.5)
cliff("mid_r", flat([(350, 150), (366, 134), (392, 129), (430, 128), (470, 131), (520, 127)], 950),
      flat([(350, 220), (520, 220)], 950), midr_m, back=300, rough=0.4, seed=3, jag=0.5)

# the central green plateau, seen from above, 110 m below the camera
lipA = [H(x, y, 110) for x, y in [(96, 222), (120, 232), (150, 240), (190, 252), (225, 246), (250, 236), (275, 243), (300, 256), (340, 262), (380, 258), (420, 250), (450, 238)]]
cliff("plateau", lipA, base(lipA), plat_m, back=330, rough=0.9, seed=4)
# green ledge at left-middle
lipB = [H(x, y, 80) for x, y in [(105, 172), (125, 180), (150, 183), (172, 180), (192, 172)]]
cliff("ledge", lipB, [(x, y + 22, d) for x, y, d in lipB], pill_m, back=260, rough=0.5, seed=6)
# left pillar
lipC = [(-25, 178, 175), (12, 153, 168), (45, 143, 160), (80, 138, 160), (108, 134, 165), (126, 138, 172), (133, 160, 176), (128, 188, 178), (140, 225, 180), (150, 262, 182), (146, 300, 184)]
cliff("pillar", lipC, base(lipC), pill_m, back=30, rise=-6, rough=0.55, seed=7, jag=0.8)
lipG = [(100, 232, 300), (135, 236, 295), (165, 244, 290), (195, 250, 288), (214, 262, 286), (222, 300, 285)]
cliff("arm", lipG, base(lipG, 360), dark_m, back=14, rise=-5, rough=0.5, seed=11, jag=0.6)
# right shelves
lipD = [H(x, y, 70) for x, y in [(352, 187), (375, 196), (396, 206), (420, 222), (450, 240), (480, 250), (515, 256)]]
cliff("shelf_r", lipD, [(x, y + 16, d) for x, y, d in lipD], dark_m, back=140, rough=0.7, seed=8, jag=0.5)
lipE = [(452, 300, 214), (447, 250, 212), (452, 215, 210), (448, 198, 208), (462, 190, 205), (490, 188, 200), (520, 186, 200)]
cliff("pillar_r", lipE, base(lipE), dark_m, back=30, rise=-6, rough=0.55, seed=9, jag=0.8)
# foreground ridge along the bottom right
lipF = [(280, 268, 150), (298, 251, 150), (330, 247, 148), (370, 255, 145), (420, 268, 140), (470, 273, 138), (520, 262, 135)]
cliff("fore", lipF, base(lipF, 380), dark_m, back=8, rise=-6, rough=0.6, seed=10, jag=0.8)

# foliage: dark trees on the plateau, green growth on the pillar, dark bushes bottom-left
for i, (px, py, r) in enumerate([(215, 212, 22), (245, 216, 26), (275, 220, 24), (300, 214, 20), (232, 205, 16), (262, 207, 18), (318, 220, 14), (200, 205, 12)]):
    x, y, d = H(px, py + 6, 110)
    kit.foliage("trees", P(px, py, d), r * 1.3, core_d, leaf_d, lumps=40, leaves=70, leaf=0.12, squash=0.6, seed=20 + i)
for i, (px, py, d, r) in enumerate([(60, 158, 140, 9), (28, 168, 142, 9), (88, 150, 142, 7), (45, 184, 138, 7), (100, 164, 144, 5), (110, 145, 148, 4), (8, 186, 140, 6)]):
    kit.foliage("growth", P(px, py, d), r, core_g, leaf_g, lumps=50, leaves=90, leaf=0.08, squash=0.8, seed=40 + i)
for i, (px, py, d, r) in enumerate([(30, 280, 70, 4), (75, 276, 72, 4.5), (115, 282, 74, 4), (160, 290, 76, 4)]):
    kit.foliage("bush", P(px, py, d), r, core_d, leaf_d, lumps=40, leaves=70, leaf=0.09, seed=50 + i)

import random
rnd = random.Random(3)
for i in range(15):   # scattered dark tree clumps over the plateau
    px, py = rnd.uniform(140, 430), rnd.uniform(202, 240); x, y, d = H(px, py + 3, 110)
    kit.foliage("scatter", P(px, py, d), rnd.uniform(4, 10), core_d, leaf_d, lumps=14, leaves=50, leaf=0.16, squash=0.55, seed=200 + i)
for i, (px, py, r) in enumerate([(372, 190, 9), (392, 198, 10), (415, 212, 12), (440, 228, 12), (468, 240, 11), (430, 205, 9), (405, 196, 7)]):   # growth along the right shelf
    x, y, d = H(px, py + 4, 70)
    kit.foliage("shelf_growth", P(px, py, d - 12), r, core_g, leaf_g, lumps=24, leaves=70, leaf=0.12, squash=0.6, seed=300 + i)
for i, (px, py, d, r) in enumerate([(468, 190, 192, 6), (492, 188, 190, 7), (455, 200, 196, 4), (400, 264, 132, 4.5), (310, 252, 142, 3)]):
    kit.foliage("dark_growth", P(px, py, d), r, core_d, leaf_d, lumps=30, leaves=70, leaf=0.1, squash=0.7, seed=320 + i)
# dark overhanging silhouettes in the top corners (unlit, painted colour)
for i, (px, py, r) in enumerate([(8, 8, 2.4), (30, 45, 1.9), (10, 82, 1.5), (-4, 108, 0.9), (40, 20, 1.3), (485, 12, 2.0), (455, 38, 1.4), (428, 52, 0.9), (492, 50, 1.4), (468, 60, 0.8), (440, 50, 1.1), (410, 60, 0.6), (470, 32, 1.5)]):
    kit.foliage("overhang", P(px, py, 28), r, sil_m, sil_m, lumps=40, leaves=60, leaf=0.1, squash=0.9, seed=60 + i)

# cloud bands between the shelves
for i, (px, py, d, r) in enumerate([(140, 186, 760, 35), (190, 185, 780, 45), (245, 187, 800, 55), (300, 186, 800, 55), (350, 187, 780, 45), (410, 190, 600, 30), (460, 192, 560, 30), (500, 191, 560, 26)]):
    kit.cloud("band", P(px, py, d), r, seed=80 + i, squash=0.16, stretch=2.6, wisp=0.45)
for i, (px, py, d, r) in enumerate([(232, 264, 300, 22), (262, 278, 280, 18), (214, 250, 330, 14), (290, 240, 340, 10)]):
    kit.cloud("low", P(px, py, d), r, density=0.7, seed=90 + i, squash=0.45, stretch=1.4)

SUN = (0.1, 0.35, -0.93)
kit.fog(0.0003, (0.78, 0.86, 0.95), size=(7000, 6000, 1300), at=(0, 2800, -590))
kit.light(SUN, 1.2, (1.0, 0.98, 0.94), (0.8, 0.85, 0.86), 1.0)
kit.sky("#98a6b0", "#bcc8ca", "#f6f8f7", "#aab4b8", strength=1.1, band_amount=0.45, elev=(0.0, 0.07, 0.2), big=("#8f9aa2", 0.85, 0.47), side=0.66, seed=2.3)
kit.render(OUT, int(WIDTH), int(SAMPLES))
print("DONE")
