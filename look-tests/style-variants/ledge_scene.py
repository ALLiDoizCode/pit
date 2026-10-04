"""PROTOTYPE, throwaway: a ledge in the pit built from rock, trees, bushes, vines and fog.
Args after --: <out.png> <flat|painted> <width> <samples>"""
import math, random, sys
import bmesh, bpy
from mathutils import Matrix, Vector, noise

OUT, STYLE, WIDTH, SAMPLES = sys.argv[sys.argv.index("--") + 1:][:4]
WIDTH, SAMPLES = int(WIDTH), int(SAMPLES)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
random.seed(11)
R = 120.0                      # pit radius

def wall_r(a, z):
    """Distance of the pit wall from the axis: lumpy, with stepped strata."""
    p = Vector((math.cos(a) * 3, math.sin(a) * 3, z / 45))
    strata = math.sin(z / 7.5 + 2.5 * noise.noise(p * 0.6))
    return R + 14 * noise.noise(p) + 5 * noise.noise(p * 3.1) + 4.5 * (1 if strata > 0.25 else 0)

HOME = Vector((0, -min(wall_r(1.5 * math.pi + d, z) for d in (-0.08, 0, 0.08) for z in (0, 2, 4)) + 1.0, 0))   # where the ledge meets the wall

def srgb(h):
    c = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]

def ramp(nt, fac, stops):
    n = nt.nodes.new("ShaderNodeValToRGB"); e = n.color_ramp.elements
    (p0, c0), (p1, c1) = stops
    e[0].position, e[0].color, e[1].position, e[1].color = p0, (*c0, 1), p1, (*c1, 1)
    nt.links.new(fac, n.inputs[0]); return n.outputs[0]

def mix(nt, blend, fac, a, b):
    n = nt.nodes.new("ShaderNodeMix"); n.data_type, n.blend_type = "RGBA", blend
    n.inputs[0].default_value = fac; nt.links.new(a, n.inputs[6]); nt.links.new(b, n.inputs[7]); return n.outputs[2]

MATS = {}
def mat(hexcol, grad=((0.55, 0.55, 0.68), (1.15, 1.1, 0.95)), ao=0.4, edge=0.03, edge_gain=0.35, world_z=None, rough=0.9):
    """One material per distinct look. In 'flat' style only the colour is used."""
    key = (hexcol, grad, ao, edge, edge_gain, world_z)
    if key in MATS: return MATS[key]
    m = bpy.data.materials.new(hexcol); nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = rough
    rgb = nt.nodes.new("ShaderNodeRGB"); rgb.outputs[0].default_value = (*srgb(hexcol), 1); cur = rgb.outputs[0]
    if STYLE == "painted":
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        if world_z:   # gradient over world height (the pit wall)
            sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs[0])
            mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value, mr.inputs[2].default_value = world_z
            nt.links.new(sep.outputs["Z"], mr.inputs[0]); fac = mr.outputs[0]
        else:         # gradient over the object's own height
            sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(nt.nodes.new("ShaderNodeTexCoord").outputs["Generated"], sep.inputs[0])
            fac = sep.outputs["Z"]
        cur = mix(nt, "MULTIPLY", 1.0, cur, ramp(nt, fac, [(0.0, grad[0]), (1.0, grad[1])]))
        if ao:
            a = nt.nodes.new("ShaderNodeAmbientOcclusion"); a.inputs["Distance"].default_value = ao
            cur = mix(nt, "MULTIPLY", 1.0, cur, ramp(nt, a.outputs["AO"], [(0.3, (0.3, 0.32, 0.45)), (0.95, (1, 1, 1))]))
        if edge:
            bev = nt.nodes.new("ShaderNodeBevel"); bev.inputs["Radius"].default_value = edge
            dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
            nt.links.new(bev.outputs[0], dot.inputs[0]); nt.links.new(geo.outputs["Normal"], dot.inputs[1])
            cur = mix(nt, "ADD", edge_gain, cur, ramp(nt, dot.outputs["Value"], [(0.8, (0.6, 0.56, 0.42)), (0.985, (0, 0, 0))]))
    nt.links.new(cur, bsdf.inputs["Base Color"]); MATS[key] = m; return m

def obj(name, bm, materials, at=(0, 0, 0), smooth=True, bevel=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in materials: me.materials.append(m)
    o = bpy.data.objects.new(name, me); o.location = at; scene.collection.objects.link(o)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    if bevel:
        b = o.modifiers.new("b", "BEVEL"); b.width, b.segments, b.limit_method, b.angle_limit, b.harden_normals = bevel, 2, "ANGLE", math.radians(28), True
    return o

def blob(name, at, radius, squash, material, seed, subdiv=3, rough=0.35, freq=1.4, smooth=True, bevel=None):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    off = Vector((seed * 1.7, seed * 0.9, seed * 2.3))
    for v in bm.verts:
        d = v.co.normalized(); v.co = d * radius * (1 + rough * noise.noise(d * freq + off)); v.co.z *= squash
    return obj(name, bm, [material], at, smooth, bevel)

LEAF = ["#2f5d3a", "#3f7a45", "#5b9a4c", "#86b85a"]
BARK, ROCK, ROCK_DARK, GRASS, VINE = "#4b3526", "#6f6a66", "#57534f", "#5d8f3f", "#2c4f33"
LEAF_GRAD = ((0.45, 0.6, 0.75), (1.3, 1.25, 0.85))

def tree(at, height, seed):
    rnd = random.Random(seed); bm = bmesh.new(); rings = []
    bend = Vector((rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5), 0)); r0 = height * 0.07
    for i in range(10):
        t = i / 9; c = bend * t * t + Vector((0, 0, height * t)); r = r0 * (1 - 0.6 * t) * (1 + 1.6 * (1 - t) ** 8)
        rings.append([bm.verts.new(c + Vector((math.cos(a) * r, math.sin(a) * r, 0))) for a in (k * math.tau / 9 for k in range(9))])
    for a, b in zip(rings, rings[1:]):
        for k in range(9): bm.faces.new((a[k], a[(k + 1) % 9], b[(k + 1) % 9], b[k]))
    obj("trunk", bm, [mat(BARK, ao=0.6, edge=0.05)], at)
    top = at + bend + Vector((0, 0, height))
    for i in range(rnd.randint(7, 10)):
        ang, dist = rnd.uniform(0, math.tau), rnd.uniform(0.3, 1.0) * height * 0.38
        p = top + Vector((math.cos(ang) * dist, math.sin(ang) * dist, rnd.uniform(-0.25, 0.22) * height))
        rad = rnd.uniform(0.16, 0.27) * height
        tone = min(3, max(0, int((p.z - top.z) / (0.12 * height) + 1.6 + rnd.uniform(-0.5, 0.5))))
        blob("canopy", p, rad, 0.72, mat(LEAF[tone], LEAF_GRAD, ao=1.2, edge=0.25, edge_gain=0.25), seed * 31 + i)

def bush(at, size, seed):
    rnd = random.Random(seed)
    for i in range(rnd.randint(3, 5)):
        p = at + Vector((rnd.uniform(-1, 1) * size, rnd.uniform(-1, 1) * size, size * rnd.uniform(0.3, 0.55)))
        blob("bush", p, size * rnd.uniform(0.55, 0.9), 0.75, mat(LEAF[rnd.randint(0, 2)], LEAF_GRAD, ao=0.5, edge=0.1, edge_gain=0.25), seed * 17 + i)

def rock(at, size, seed, squash=0.7):
    blob("rock", at + Vector((0, 0, size * squash * 0.35)), size, squash, mat(ROCK, ao=0.5, edge=0.06), seed, subdiv=2, rough=0.5, freq=1.1, bevel=size * 0.05)

def clamped_slab(name, at, size, top_mat, side_mat, seed, flat_top=True):
    """A rocky mass with one flat face: a ledge (flat on top) or an overhang (flat underneath).
    Built on a polar grid so the flat face never folds over itself."""
    bm = bmesh.new(); K, N = 12, 56; off = Vector((seed, seed * 2, seed * 3)); sign = -1 if flat_top else 1
    def outline(phi):
        d = Vector((math.cos(phi), math.sin(phi), 0))
        return 1 + 0.28 * noise.noise(d * 1.5 + off) + 0.1 * noise.noise(d * 4.0 + off)
    centre_top = bm.verts.new((0, 0, 0)); centre_bot = bm.verts.new((0, 0, sign * size.z))
    top, bot = [], []
    for k in range(1, K + 1):
        t = k / K; tr, br = [], []
        for i in range(N):
            phi = i * math.tau / N; o = outline(phi); x, y = math.cos(phi) * size.x * o * t, math.sin(phi) * size.y * o * t
            tr.append(bm.verts.new((x, y, 0)))
            depth = size.z * math.sqrt(max(0.0, 1 - t * t)) * (1 + 0.35 * noise.noise(Vector((x, y, 0)) * 0.12 + off))
            br.append(tr[-1] if k == K else bm.verts.new((x, y, sign * depth)))
        top.append(tr); bot.append(br)
    def cap(rows, centre, slot, flip):
        for i in range(N):
            f = bm.faces.new((centre, rows[0][i], rows[0][(i + 1) % N])); f.material_index = slot
            if flip: f.normal_flip()
        for ra, rb in zip(rows, rows[1:]):
            for i in range(N):
                f = bm.faces.new((ra[i], rb[i], rb[(i + 1) % N], ra[(i + 1) % N])); f.material_index = slot
                if flip: f.normal_flip()
    cap(top, centre_top, 0 if flat_top else 1, not flat_top)
    cap(bot, centre_bot, 1, flat_top)
    o = obj(name, bm, [top_mat, side_mat], at, smooth=True)
    o.data.set_sharp_from_angle(angle=math.radians(40))
    return o

# ---- the pit wall: a ring of stratified rock, seen from inside
def wall():
    bm = bmesh.new(); N, M, z0, dz = 220, 150, -300.0, 3.2; rows = []
    for j in range(M):
        z = z0 + j * dz; row = []
        for i in range(N):
            a = i * math.tau / N; r = wall_r(a, z)
            if abs(a - 1.5 * math.pi) < 0.45 and -40 < z < 70: r = max(r, -HOME.y + 1.0)
            row.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        for i in range(N): bm.faces.new((a[i], b[i], b[(i + 1) % N], a[(i + 1) % N]))
    o = obj("wall", bm, [mat("#7a6f66", ((0.35, 0.42, 0.6), (1.2, 1.1, 0.95)), ao=6.0, edge=0.8, edge_gain=0.22, world_z=(-220, 120))], smooth=True)
    o.data.set_sharp_from_angle(angle=math.radians(35))
wall()

# vegetation clinging to the wall, all the way round and down
for i in range(1500):
    a, z = random.uniform(0, math.tau), random.uniform(-230, 110)
    if abs(a - 1.5 * math.pi) < 0.25 and abs(z) < 30: continue
    r = wall_r(a, z) + random.uniform(0.3, 1.2); s = random.uniform(1.4, 4.2)
    blob("moss", Vector((math.cos(a) * r, math.sin(a) * r, z)), s, 0.8, mat(LEAF[random.randint(0, 3)], LEAF_GRAD, ao=3.0, edge=0.5, edge_gain=0.2), i, subdiv=2)

# ---- the ledge we stand on, and an overhang above it
ledge = clamped_slab("ledge", HOME + Vector((0, 6, 0)), Vector((17, 15, 9)), mat(GRASS, ((0.8, 0.85, 0.8), (1.1, 1.1, 0.9)), ao=0.8, edge=0), mat(ROCK_DARK, ao=3.0, edge=0.4), 3)
clamped_slab("overhang", HOME + Vector((-10, 10, 7.5)), Vector((12, 16, 6)), mat(ROCK_DARK), mat(ROCK_DARK, ao=3.0, edge=0.4), 8, flat_top=False)
EDGE = max(v.co.y for v in ledge.data.vertices if abs(v.co.x) < 3 and v.co.z > -0.3) + ledge.location.y - HOME.y   # ledge edge, metres out from the wall
for k, (phi, z, size) in enumerate([(35, -26, 20), (-28, -52, 24), (62, -74, 22), (-58, -14, 18), (12, -110, 26), (-85, -90, 22)]):
    a = math.radians(phi); c = Vector((math.sin(a) * (R - 14), -math.cos(a) * (R - 14), z))
    clamped_slab("far_ledge", c, Vector((size, size * 0.8, size * 0.5)), mat(GRASS, ao=0.8, edge=0), mat(ROCK_DARK, ao=3.0, edge=0.4), 20 + k)
    for t in range(4):
        tree(c + Vector((random.uniform(-0.5, 0.5) * size, random.uniform(-0.4, 0.4) * size, 0)), random.uniform(6, 10), 100 + k * 10 + t)
    for t in range(4): bush(c + Vector((random.uniform(-0.6, 0.6) * size, random.uniform(-0.5, 0.5) * size, 0)), random.uniform(0.8, 1.6), 300 + k * 10 + t)

tree(HOME + Vector((5.2, EDGE - 5.0, 0)), 3.4, 1); tree(HOME + Vector((-7.5, EDGE - 4.5, 0)), 4.2, 2); tree(HOME + Vector((11, 5, 0)), 8.5, 3)
for i, (x, y, s) in enumerate([(-3.6, -1.6, 0.7), (2.4, -0.8, 0.5), (8.5, -3, 0.9), (-9, -7, 1.0), (-1.2, -5.5, 0.4), (6.5, -1.2, 0.5)]): bush(HOME + Vector((x, EDGE + y, 0)), s, i + 40)
for i, (x, y, s) in enumerate([(-2.4, -3.4, 0.8), (3.6, -2.2, 0.5), (0.8, -1.0, 0.3), (-6, -1.5, 0.6), (9, -6, 1.2)]): rock(HOME + Vector((x, EDGE + y, 0)), s, i + 70)

# grass tufts
tuft = bmesh.new()
for k in range(6):
    r = bmesh.ops.create_cone(tuft, cap_ends=False, segments=4, radius1=0.02, radius2=0.0, depth=0.24)
    a = k * math.tau / 6
    bmesh.ops.transform(tuft, matrix=Matrix.Translation((math.cos(a) * 0.04, math.sin(a) * 0.04, 0.11)) @ Matrix.Rotation(0.35, 4, Vector((-math.sin(a), math.cos(a), 0))), verts=r["verts"])
tuft_obj = obj("tuft", tuft, [mat("#6fa548", ((0.6, 0.7, 0.6), (1.3, 1.3, 0.9)), ao=0, edge=0)], HOME + Vector((0, 4, 0)))
for i in range(2600):
    x, y = random.uniform(-13, 13), random.uniform(1, EDGE - 0.4)
    if (x / 14) ** 2 + ((y - 6) / (EDGE - 5.6)) ** 2 > 0.95: continue
    t = bpy.data.objects.new("tuft", tuft_obj.data); t.location = HOME + Vector((x, y, 0))
    t.rotation_euler.z = random.uniform(0, 6.3); t.scale = (random.uniform(0.6, 1.5),) * 3; scene.collection.objects.link(t)

# vines hanging from the overhang
for i in range(16):
    x, y = random.uniform(-9, -2.5), random.uniform(EDGE - 6, EDGE + 2); length = random.uniform(2.0, 6.5)
    cu = bpy.data.curves.new("vine", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = random.uniform(0.025, 0.05); cu.bevel_resolution = 2
    sp = cu.splines.new("POLY"); n = 14; sp.points.add(n - 1); sway = random.uniform(0, 6)
    for k in range(n):
        t = k / (n - 1); sp.points[k].co = (x + 0.25 * math.sin(sway + t * 5), HOME.y + y + 0.2 * math.cos(sway + t * 4), 7.8 - t * length, 1)
    cu.materials.append(mat(VINE, ao=0, edge=0)); scene.collection.objects.link(bpy.data.objects.new("vine", cu))
    for k in range(3, n, 3):
        p = sp.points[k].co
        blob("vine_leaf", Vector((p.x, p.y, p.z)), random.uniform(0.12, 0.22), 0.6, mat(LEAF[random.randint(1, 3)], LEAF_GRAD, ao=0, edge=0), i * 9 + k, subdiv=1)

# a 1.8 m figure near the edge, for scale, and a crate
fig = bmesh.new(); bmesh.ops.create_cone(fig, cap_ends=True, segments=12, radius1=0.22, radius2=0.15, depth=1.55, matrix=Matrix.Translation((0, 0, 0.775)))
bmesh.ops.create_uvsphere(fig, u_segments=12, v_segments=8, radius=0.125, matrix=Matrix.Translation((0, 0, 1.675)))
obj("figure", fig, [mat("#b5452f", ao=0.3, edge=0.02)], HOME + Vector((2.6, EDGE - 1.0, 0)))
cr = bmesh.new(); bmesh.ops.create_cube(cr, size=0.8, matrix=Matrix.Translation((0, 0, 0.4)))
obj("crate", cr, [mat("#8a6238", ao=0.3, edge=0.03)], HOME + Vector((-1.4, EDGE - 3.8, 0)), smooth=True, bevel=0.03)

# ---- light, fog, camera
world = bpy.data.worlds.new("w"); scene.world = world; nt = world.node_tree
bg = nt.nodes["Background"]; bg.inputs["Color"].default_value = (0.42, 0.62, 0.66, 1); bg.inputs["Strength"].default_value = 3.0
# Fog fills a box around the pit. (A world volume is infinite and would black out the sun.)
fogm = bpy.data.materials.new("fog"); fnt = fogm.node_tree; fnt.nodes.remove(fnt.nodes["Principled BSDF"])
vol = fnt.nodes.new("ShaderNodeVolumeScatter"); vol.inputs["Color"].default_value = (0.72, 0.88, 0.9, 1)
vol.inputs["Density"].default_value = 0.0026; vol.inputs["Anisotropy"].default_value = 0.35
fnt.links.new(vol.outputs[0], next(n for n in fnt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Volume"])
fb = bmesh.new(); bmesh.ops.create_cube(fb, size=1.0, matrix=Matrix.Translation((0, 0, -60)) @ Matrix.Diagonal((330, 330, 470, 1)))
obj("fog", fb, [fogm], smooth=False)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 9.0; sun.data.angle = math.radians(2); sun.data.color = (1.0, 0.9, 0.72)
sun.rotation_euler = Vector((0.42, 0.5, -0.76)).to_track_quat("-Z", "Y").to_euler(); scene.collection.objects.link(sun)

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(cam); scene.camera = cam
cam.data.lens = 24; cam.data.clip_end = 2000
cam.location = HOME + Vector((0.6, EDGE - 9.0, 1.7)); target = cam.location + Vector((0.3, 1.0, -0.2)) * 50
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()

scene.render.engine = "CYCLES"; scene.cycles.samples = SAMPLES; scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4; scene.cycles.volume_bounces = 1; scene.cycles.volume_step_rate = 4
scene.render.resolution_x, scene.render.resolution_y = WIDTH, WIDTH * 9 // 16
scene.view_settings.view_transform = "Filmic" if "Filmic" in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "AgX"
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("DONE")
