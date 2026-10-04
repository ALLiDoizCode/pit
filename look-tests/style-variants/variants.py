"""PROTOTYPE, throwaway: the same crate and rock in three styles, to pick a look by eye."""
import math, random, sys
import bmesh, bpy
from mathutils import Matrix, Vector, noise

OUT = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def srgb(h):
    c = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]

def mat(name, hexcol, rough=0.8, jitter=0.0):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    r, g, bl = srgb(hexcol)
    k = 1 + jitter
    b.inputs["Base Color"].default_value = (r * k, g * k, bl * k, 1)
    b.inputs["Roughness"].default_value = rough
    return m

def obj_from_bm(name, bm, materials, at):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in materials: me.materials.append(m)
    o = bpy.data.objects.new(name, me); o.location = at
    scene.collection.objects.link(o); return o

def add_box(bm, centre, size, rot=None, slot=0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    m = Matrix.Translation(centre) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal((*size, 1))
    bmesh.ops.transform(bm, matrix=m, verts=r["verts"])
    for f in {f for v in r["verts"] for f in v.link_faces}: f.material_index = slot

def soften(o, width, segments=2):
    """Bevel every hard edge and shade smooth, so edges catch light and faces stay flat."""
    for p in o.data.polygons: p.use_smooth = True
    b = o.modifiers.new("bevel", "BEVEL")
    b.width, b.segments, b.limit_method, b.angle_limit = width, segments, "ANGLE", math.radians(30)
    b.harden_normals = True

FRAME, PANEL, IRON = "#4a2e1a", "#a87a4a", "#3a3d42"
X, Y, Z = Vector((1,0,0)), Vector((0,1,0)), Vector((0,0,1))
FACES = [(X, Y, Z), (-X, Z, Y), (Y, Z, X), (-Y, X, Z), (Z, X, Y)]

def crate_simple(at, bevel):
    S, F, R = 0.8, 0.1, 0.05
    bm = bmesh.new(); c = Vector((0, 0, S/2)); h = S/2
    add_box(bm, c, (S - 2*R, S - 2*R, S - 2*R), slot=1)             # panels
    for a in (-1, 1):
        for b in (-1, 1):                                            # 12 frame members
            add_box(bm, c + Vector((a*(h-F/2), b*(h-F/2), 0)), (F, F, S))
            add_box(bm, c + Vector((a*(h-F/2), 0, b*(h-F/2))), (F, S, F))
            add_box(bm, c + Vector((0, a*(h-F/2), b*(h-F/2))), (S, F, F))
    o = obj_from_bm("crate", bm, [mat("f", FRAME), mat("p", PANEL)], at)
    if bevel: soften(o, 0.012)
    return o

def crate_detailed(at):
    S, F, R = 0.8, 0.1, 0.05
    random.seed(3)
    mats = [mat("f", FRAME), mat("iron", IRON, 0.5)] + [mat(f"p{i}", PANEL, jitter=random.uniform(-0.18, 0.12)) for i in range(5)]
    bm = bmesh.new(); c = Vector((0, 0, S/2)); h = S/2
    add_box(bm, c, (S - 2*R - 0.02, S - 2*R - 0.02, S - 2*R - 0.02), slot=0)   # dark core seen through plank gaps
    for a in (-1, 1):
        for b in (-1, 1):
            add_box(bm, c + Vector((a*(h-F/2), b*(h-F/2), 0)), (F, F, S))
            add_box(bm, c + Vector((a*(h-F/2), 0, b*(h-F/2))), (F, S, F))
            add_box(bm, c + Vector((0, a*(h-F/2), b*(h-F/2))), (S, F, F))
    inner = S - 2*F; n = 4; gap = 0.012; w = (inner - gap*(n-1)) / n
    for normal, u, v in FACES:
        fc = c + normal * (h - R - 0.01)
        basis = Matrix((u, v, normal)).transposed().to_4x4()
        for i in range(n):                                           # planks
            off = -inner/2 + w/2 + i*(w+gap)
            add_box(bm, fc + u*off, (w, inner + 0.02, 0.02), rot=basis, slot=2 + random.randrange(5))
        if normal.z == 0:                                            # diagonal brace on the sides
            add_box(bm, fc + normal*0.02, (0.08, inner*1.38, 0.03), rot=basis @ Matrix.Rotation(math.radians(45), 4, "Z"), slot=0)
    for a in (-1, 1):
        for b in (-1, 1):
            for d in (-1, 1):                                        # iron corner caps
                add_box(bm, c + Vector((a*(h-0.05), b*(h-0.05), d*(h-0.05))) * 1.006, (0.115, 0.115, 0.115), slot=1)
    o = obj_from_bm("crate_detailed", bm, mats, at)
    soften(o, 0.008, 3)
    return o

def rock(at, subdiv, smooth, bevel=False, seed=7):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=0.55)
    off = Vector((seed, seed * 2.3, seed * 0.7))
    for v in bm.verts:
        d = v.co.normalized()
        n = noise.noise(d * 1.3 + off) * 0.38 + (noise.noise(d * 3.1 + off) * 0.12 if subdiv > 2 else 0)
        v.co = d * 0.55 * (1 + n)
        v.co.z *= 0.75
    lowest = min(v.co.z for v in bm.verts)
    for v in bm.verts: v.co.z -= lowest + 0.08
    o = obj_from_bm("rock", bm, [mat("r", "#6b6f78", 0.95)], at)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if bevel: soften(o, 0.03, 2)
    return o

SPACING = 8.0
crate_simple(Vector((-SPACING, 0, 0)), bevel=False); rock(Vector((-SPACING, 1.6, 0)), 1, smooth=False)
crate_simple(Vector((0, 0, 0)), bevel=True);         rock(Vector((0, 1.6, 0)), 2, smooth=False, bevel=True)
crate_detailed(Vector((SPACING, 0, 0)));             rock(Vector((SPACING, 1.6, 0)), 5, smooth=True)

bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=40)
obj_from_bm("ground", bm, [mat("g", "#5d5a52", 1.0)], Vector((0, 0, 0)))

world = bpy.data.worlds.new("w"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.35, 0.45, 0.6, 1); bg.inputs["Strength"].default_value = 0.6
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 4.0; sun.data.angle = math.radians(3)
sun.data.color = (1.0, 0.92, 0.8)
sun.rotation_euler = Vector((0.5, 0.7, -0.75)).to_track_quat("-Z", "Y").to_euler(); scene.collection.objects.link(sun)

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(cam); scene.camera = cam
cam.data.lens = 35
scene.render.engine = "BLENDER_EEVEE"; scene.eevee.taa_render_samples = 64
try: scene.eevee.use_raytracing = True
except Exception: pass
scene.render.resolution_x, scene.render.resolution_y = 900, 900
scene.view_settings.view_transform = "Standard"

for i, label in enumerate("ABC"):
    x = (i - 1) * SPACING
    target = Vector((x, 0.6, 0.4))
    cam.location = Vector((x + 1.5, -2.0, 1.55))          # roughly eye height, 2.5 m away
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = f"{OUT}/{label}.png"
    bpy.ops.render.render(write_still=True)
tris = {o.name: sum(len(p.vertices) - 2 for p in o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.polygons) for o in scene.objects if o.type == "MESH" and o.name != "ground"}
print("TRIS", tris)
