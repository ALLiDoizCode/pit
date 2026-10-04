"""PROTOTYPE, throwaway: one crate and two rocks under four surface treatments, far and near."""
import math, random, sys
import bmesh, bpy
from mathutils import Matrix, Vector, noise

OUT = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def srgb(h):
    c = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]

def ramp(nt, fac, stops):
    n = nt.nodes.new("ShaderNodeValToRGB")
    e = n.color_ramp.elements
    (p0, c0), (p1, c1) = stops
    e[0].position, e[0].color, e[1].position, e[1].color = p0, (*c0, 1), p1, (*c1, 1)
    nt.links.new(fac, n.inputs[0]); return n.outputs[0]

def mix(nt, blend, fac, a, b):
    n = nt.nodes.new("ShaderNodeMix"); n.data_type, n.blend_type = "RGBA", blend
    n.inputs[0].default_value = fac
    nt.links.new(a, n.inputs[6])
    if hasattr(b, "node"): nt.links.new(b, n.inputs[7])
    else: n.inputs[7].default_value = (*b, 1)
    return n.outputs[2]

def mat(name, hexcol, kind, style, rough=0.8, jitter=0.0):
    """kind: wood | iron | rock | ground.  style: flat | pbr | painted | painterly."""
    m = bpy.data.materials.new(f"{style}_{name}"); nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = rough
    if kind == "iron": bsdf.inputs["Metallic"].default_value = 0.0
    rgb = nt.nodes.new("ShaderNodeRGB"); k = 1 + jitter
    rgb.outputs[0].default_value = (*[c * k for c in srgb(hexcol)], 1)
    cur = rgb.outputs[0]
    coord = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")

    if style == "pbr" and kind != "ground":
        mp = nt.nodes.new("ShaderNodeMapping"); nt.links.new(coord, mp.inputs[0])
        mp.inputs["Scale"].default_value = (14, 14, 0.7) if kind == "wood" else (5, 5, 5)
        n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 2.5; n1.inputs["Detail"].default_value = 9
        nt.links.new(mp.outputs[0], n1.inputs["Vector"])
        cur = mix(nt, "MULTIPLY", 1.0, cur, ramp(nt, n1.outputs[0], [(0.3, (0.55,)*3), (0.75, (1.25,)*3)]))
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 9 if kind == "wood" else 14; n2.inputs["Detail"].default_value = 10
        nt.links.new(mp.outputs[0], n2.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35 if kind != "iron" else 0.15
        nt.links.new(n2.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
        nt.links.new(ramp(nt, n2.outputs[0], [(0.2, (0.45,)*3), (0.8, (0.95,)*3)]), bsdf.inputs["Roughness"])

    if style in ("painted", "painterly") and kind != "ground":
        # darker toward the ground, lighter toward the top
        sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs[0])
        cur = mix(nt, "MULTIPLY", 1.0, cur, ramp(nt, sep.outputs["Z"], [(0.0, (0.55, 0.52, 0.6)), (0.85, (1.12, 1.08, 1.0))]))
        # shadow painted into crevices
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.25
        cur = mix(nt, "MULTIPLY", 1.0, cur, ramp(nt, ao.outputs["AO"], [(0.35, (0.35, 0.33, 0.42)), (0.95, (1, 1, 1))]))
        # light painted along exposed edges
        bev = nt.nodes.new("ShaderNodeBevel"); bev.inputs["Radius"].default_value = 0.02 if kind != "rock" else 0.06
        dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs[0], dot.inputs[0]); nt.links.new(geo.outputs["Normal"], dot.inputs[1])
        edge = ramp(nt, dot.outputs["Value"], [(0.80, (0.55, 0.5, 0.4)), (0.985, (0, 0, 0))])
        cur = mix(nt, "ADD", 0.55 if kind != "rock" else 0.3, cur, edge)

    if style == "painterly" and kind != "ground":
        # brush-stroke patches: each patch shifts value and hue a little
        wn = nt.nodes.new("ShaderNodeTexNoise"); wn.inputs["Scale"].default_value = 3.0
        nt.links.new(coord, wn.inputs["Vector"])
        warp = nt.nodes.new("ShaderNodeVectorMath"); warp.operation = "ADD"
        nt.links.new(coord, warp.inputs[0]); nt.links.new(wn.outputs["Color"], warp.inputs[1])
        vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 4.5 if kind != "rock" else 3.0
        nt.links.new(warp.outputs[0], vor.inputs["Vector"])
        hsv = nt.nodes.new("ShaderNodeHueSaturation")
        sepc = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(vor.outputs["Color"], sepc.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[3].default_value, mr.inputs[4].default_value = 0.488, 0.512
        nt.links.new(sepc.outputs[0], mr.inputs[0]); nt.links.new(mr.outputs[0], hsv.inputs["Hue"])
        mv = nt.nodes.new("ShaderNodeMapRange"); mv.inputs[3].default_value, mv.inputs[4].default_value = 0.86, 1.14
        nt.links.new(sepc.outputs[1], mv.inputs[0]); nt.links.new(mv.outputs[0], hsv.inputs["Value"])
        nt.links.new(cur, hsv.inputs["Color"]); cur = hsv.outputs[0]

    nt.links.new(cur, bsdf.inputs["Base Color"])
    return m

def obj_from_bm(name, bm, materials, at):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in materials: me.materials.append(m)
    o = bpy.data.objects.new(name, me); o.location = at
    scene.collection.objects.link(o); return o

def add_box(bm, centre, size, rot=None, slot=0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(centre) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal((*size, 1)), verts=r["verts"])
    for f in {f for v in r["verts"] for f in v.link_faces}: f.material_index = slot

def soften(o, width, segments=2):
    for p in o.data.polygons: p.use_smooth = True
    b = o.modifiers.new("bevel", "BEVEL")
    b.width, b.segments, b.limit_method, b.angle_limit, b.harden_normals = width, segments, "ANGLE", math.radians(30), True

FRAME, PANEL, IRON = "#4a2e1a", "#a87a4a", "#3a3d42"
X, Y, Z = Vector((1,0,0)), Vector((0,1,0)), Vector((0,0,1))
FACES = [(X, Y, Z), (-X, Z, Y), (Y, Z, X), (-Y, X, Z), (Z, X, Y)]

def crate(at, style):
    S, F, R = 0.8, 0.1, 0.05
    random.seed(3)
    mats = [mat("frame", FRAME, "wood", style), mat("iron", IRON, "iron", style, 0.5)] + [
        mat(f"plank{i}", PANEL, "wood", style, jitter=random.uniform(-0.18, 0.12)) for i in range(5)]
    bm = bmesh.new(); c = Vector((0, 0, S/2)); h = S/2
    add_box(bm, c, (S - 2*R - 0.02,) * 3, slot=0)
    for a in (-1, 1):
        for b in (-1, 1):
            add_box(bm, c + Vector((a*(h-F/2), b*(h-F/2), 0)), (F, F, S))
            add_box(bm, c + Vector((a*(h-F/2), 0, b*(h-F/2))), (F, S, F))
            add_box(bm, c + Vector((0, a*(h-F/2), b*(h-F/2))), (S, F, F))
    inner = S - 2*F; n = 4; gap = 0.012; w = (inner - gap*(n-1)) / n
    for normal, u, v in FACES:
        fc = c + normal * (h - R - 0.01); basis = Matrix((u, v, normal)).transposed().to_4x4()
        for i in range(n):
            add_box(bm, fc + u*(-inner/2 + w/2 + i*(w+gap)), (w, inner + 0.02, 0.02), rot=basis, slot=2 + random.randrange(5))
        if normal.z == 0:
            add_box(bm, fc + normal*0.02, (0.08, inner*1.38, 0.03), rot=basis @ Matrix.Rotation(math.radians(45), 4, "Z"), slot=0)
    for a in (-1, 1):
        for b in (-1, 1):
            for d in (-1, 1):
                add_box(bm, c + Vector((a*(h-0.05), b*(h-0.05), d*(h-0.05))) * 1.006, (0.115,) * 3, slot=1)
    soften(obj_from_bm("crate", bm, mats, at), 0.008, 3)

def rock(at, style, subdiv, smooth, bevel, seed):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=0.55)
    off = Vector((seed, seed * 2.3, seed * 0.7))
    for v in bm.verts:
        d = v.co.normalized()
        v.co = d * 0.55 * (1 + noise.noise(d * 1.3 + off) * 0.38 + (noise.noise(d * 3.1 + off) * 0.12 if subdiv > 2 else 0))
        v.co.z *= 0.75
    low = min(v.co.z for v in bm.verts)
    for v in bm.verts: v.co.z -= low + 0.08
    o = obj_from_bm("rock", bm, [mat("rock", "#6b6f78", "rock", style, 0.95)], at)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if bevel: soften(o, 0.03, 2)

STYLES = ["flat", "pbr", "painted", "painterly"]
SPACING = 9.0
for i, style in enumerate(STYLES):
    x = i * SPACING
    crate(Vector((x, 0, 0)), style)
    rock(Vector((x - 1.3, 1.5, 0)), style, 2, False, True, 7)       # B rock: flat faces, soft edges
    rock(Vector((x + 0.5, 1.7, 0)), style, 5, True, False, 11)      # C rock: smooth

bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=80)
obj_from_bm("ground", bm, [mat("ground", "#5d5a52", "ground", "flat", 1.0)], Vector((0, 0, 0)))

world = bpy.data.worlds.new("w"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.35, 0.45, 0.6, 1); bg.inputs["Strength"].default_value = 0.6
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 4.0; sun.data.angle = math.radians(3); sun.data.color = (1.0, 0.92, 0.8)
sun.rotation_euler = Vector((0.5, 0.7, -0.75)).to_track_quat("-Z", "Y").to_euler(); scene.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(cam); scene.camera = cam

scene.render.engine = "CYCLES"
scene.cycles.samples = 96; scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 800
scene.view_settings.view_transform = "Standard"

SHOTS = {"far": (Vector((1.6, -2.1, 1.55)), Vector((-0.2, 0.7, 0.4)), 35), "near": (Vector((0.75, -0.75, 1.15)), Vector((0.2, -0.2, 0.55)), 35)}
for i, style in enumerate(STYLES):
    base = Vector((i * SPACING, 0, 0))
    for shot, (pos, target, lens) in SHOTS.items():
        cam.data.lens = lens; cam.location = base + pos
        cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = f"{OUT}/{shot}_{style}.png"
        bpy.ops.render.render(write_still=True)
print("DONE")
