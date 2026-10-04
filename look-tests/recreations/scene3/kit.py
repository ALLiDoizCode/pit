"""PROTOTYPE, throwaway: building blocks for recreating reference scenes in Blender.

Geometry is placed by where it sits in the reference image: P(px, py, distance) is the
world point seen at that pixel of the reference, that far from the camera.
"""
import math, random
import bmesh, bpy
from mathutils import Matrix, Vector, noise

scene = None
CAM = None
REF_W = REF_H = 1.0
LAST_RIM = None

def setup(ref_w, ref_h, lens=40.0, pitch_deg=-14.0, cam_z=0.0):
    global scene, CAM, REF_W, REF_H
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene; REF_W, REF_H = ref_w, ref_h
    CAM = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); scene.collection.objects.link(CAM); scene.camera = CAM
    CAM.data.lens = lens; CAM.data.clip_end = 20000; CAM.location = (0, 0, cam_z)
    CAM.rotation_euler = (math.radians(90 + pitch_deg), 0, 0)
    scene.render.resolution_x, scene.render.resolution_y = int(ref_w), int(ref_h)
    bpy.context.view_layer.update()
    return scene

def P(px, py, d):
    """World point seen at reference pixel (px, py), d metres from the camera."""
    half_w = 18.0 / CAM.data.lens                 # tan(hfov/2) for a 36 mm sensor
    half_h = half_w * REF_H / REF_W
    u = (px - REF_W / 2) / (REF_W / 2) * half_w
    v = (REF_H / 2 - py) / (REF_H / 2) * half_h
    return CAM.matrix_world @ (Vector((u, v, -1)).normalized() * d)

def srgb(h):
    c = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]

def _ramp(nt, fac, stops):
    n = nt.nodes.new("ShaderNodeValToRGB"); e = n.color_ramp.elements
    while len(e) < len(stops): e.new(0.5)
    for el, (p, c) in zip(e, stops): el.position, el.color = p, (*srgb(c), 1) if isinstance(c, str) else (*c, 1)
    nt.links.new(fac, n.inputs[0]); return n.outputs[0]

def _mix(nt, blend, fac, a, b):
    n = nt.nodes.new("ShaderNodeMix"); n.data_type, n.blend_type = "RGBA", blend
    if hasattr(fac, "node"): nt.links.new(fac, n.inputs[0])
    else: n.inputs[0].default_value = fac
    nt.links.new(a, n.inputs[6]); nt.links.new(b, n.inputs[7]); return n.outputs[2]

def rock_material(name, rock=("#2e2a2b", "#5b5352", "#8a7d76"), grass=("#3f8f2a", "#7fd036"), streak=1.0, grass_from=0.62, patch=None, moss=None, patch_scale=0.02, tilt=0.0, zscale=0.012):
    """Rock on steep faces, with vertical streaks; grass wherever the surface faces up."""
    m = bpy.data.materials.new(name); nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.0      # no grazing-angle sheen: faces seen edge-on otherwise go pale grey
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mp = nt.nodes.new("ShaderNodeMapping"); nt.links.new(geo.outputs["Position"], mp.inputs[0]); mp.inputs["Scale"].default_value = (0.09, 0.09, zscale); mp.inputs["Rotation"].default_value = (0, tilt, 0)
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = streak; n1.inputs["Detail"].default_value = 8; nt.links.new(mp.outputs[0], n1.inputs["Vector"])
    rock_c = _ramp(nt, n1.outputs[0], [(0.3, rock[0]), (0.55, rock[1]), (0.8, rock[2])])
    if patch:   # broad painted patches of a second rock colour (worn, sunlit or mineral faces)
        pn = nt.nodes.new("ShaderNodeTexNoise"); pn.inputs["Scale"].default_value = patch_scale; pn.inputs["Detail"].default_value = 5; pn.inputs["Roughness"].default_value = 0.65
        nt.links.new(geo.outputs["Position"], pn.inputs["Vector"])
        pr = nt.nodes.new("ShaderNodeRGB"); pr.outputs[0].default_value = (*srgb(patch), 1)
        rock_c = _mix(nt, "MIX", _ramp(nt, pn.outputs[0], [(0.5, (0, 0, 0)), (0.62, (0.85, 0.85, 0.85))]), rock_c, _mix(nt, "MULTIPLY", 0.5, pr.outputs[0], rock_c))
    if moss:    # moss and hanging growth in patches on the faces
        mn = nt.nodes.new("ShaderNodeTexNoise"); mn.inputs["Scale"].default_value = patch_scale * 2.3; mn.inputs["Detail"].default_value = 7; mn.inputs["Roughness"].default_value = 0.7
        mo = nt.nodes.new("ShaderNodeVectorMath"); mo.operation = "ADD"; mo.inputs[1].default_value = (37, 11, 5); nt.links.new(geo.outputs["Position"], mo.inputs[0]); nt.links.new(mo.outputs[0], mn.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeRGB"); mr.outputs[0].default_value = (*srgb(moss), 1)
        rock_c = _mix(nt, "MIX", _ramp(nt, mn.outputs[0], [(0.52, (0, 0, 0)), (0.6, (1, 1, 1))]), rock_c, mr.outputs[0])
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 0.25; n2.inputs["Detail"].default_value = 6; nt.links.new(geo.outputs["Position"], n2.inputs["Vector"])
    grass_c = _ramp(nt, n2.outputs[0], [(0.35, grass[0]), (0.7, grass[1])])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    # break the grass line up with noise so it creeps over the lip unevenly
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"; nt.links.new(sep.outputs["Z"], add.inputs[0])
    sc = nt.nodes.new("ShaderNodeMath"); sc.operation = "MULTIPLY_ADD"; sc.inputs[1].default_value = 0.5; sc.inputs[2].default_value = -0.25
    nt.links.new(n2.outputs[0], sc.inputs[0]); nt.links.new(sc.outputs[0], add.inputs[1])
    mask = _ramp(nt, add.outputs[0], [(grass_from, (0, 0, 0)), (grass_from + 0.08, (1, 1, 1))])
    nt.links.new(_mix(nt, "MIX", mask, rock_c, grass_c), bsdf.inputs["Base Color"])
    n3 = nt.nodes.new("ShaderNodeTexNoise"); n3.inputs["Scale"].default_value = 0.6 * streak; n3.inputs["Detail"].default_value = 10; nt.links.new(mp.outputs[0], n3.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.8; bump.inputs["Distance"].default_value = 3.0
    nt.links.new(n3.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    return m

def puff_material(name, shade, mid, light, speckle=None, soft=0.75, emit=0.0):
    """Billowy masses (foliage, cloud): shaded as one soft volume, not as separate lumps."""
    m = bpy.data.materials.new(name); nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 1.0
    geo = nt.nodes.new("ShaderNodeNewGeometry"); tc = nt.nodes.new("ShaderNodeTexCoord")
    nrm = nt.nodes.new("ShaderNodeVectorMath"); nrm.operation = "NORMALIZE"; nt.links.new(tc.outputs["Object"], nrm.inputs[0])
    vt = nt.nodes.new("ShaderNodeVectorTransform"); vt.vector_type, vt.convert_from, vt.convert_to = "NORMAL", "OBJECT", "WORLD"; nt.links.new(nrm.outputs[0], vt.inputs[0])
    mixn = nt.nodes.new("ShaderNodeMix"); mixn.data_type = "VECTOR"; mixn.inputs[0].default_value = soft
    nt.links.new(geo.outputs["Normal"], mixn.inputs[4]); nt.links.new(vt.outputs[0], mixn.inputs[5])
    nn = nt.nodes.new("ShaderNodeVectorMath"); nn.operation = "NORMALIZE"; nt.links.new(mixn.outputs[1], nn.inputs[0])
    nt.links.new(nn.outputs[0], bsdf.inputs["Normal"])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(nn.outputs[0], sep.inputs[0])
    col = _ramp(nt, sep.outputs["Z"], [(0.25, shade), (0.6, mid), (0.9, light)])
    if speckle:   # scattered bright leaf-glints, as painted foliage has
        vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = speckle[1]; nt.links.new(geo.outputs["Position"], vor.inputs["Vector"])
        dots = _ramp(nt, vor.outputs["Distance"], [(0.16, (1, 1, 1)), (0.24, (0, 0, 0))])
        lit = _ramp(nt, sep.outputs["Z"], [(0.35, (0, 0, 0)), (0.75, (1, 1, 1))])
        both = _mix(nt, "MULTIPLY", 1.0, dots, lit)
        rgb = nt.nodes.new("ShaderNodeRGB"); rgb.outputs[0].default_value = (*srgb(speckle[0]), 1)
        col = _mix(nt, "MIX", both, col, rgb.outputs[0])
    nt.links.new(col, bsdf.inputs["Base Color"])
    if emit:
        nt.links.new(col, bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = emit
    return m

def _obj(name, bm, material, at=(0, 0, 0), smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(material)
    o = bpy.data.objects.new(name, me); o.location = at; scene.collection.objects.link(o)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return o

def puff(name, centre, radius, material, n=70, squash=0.8, seed=0, lump=(0.2, 0.36), stretch=(1, 1, 1), subdiv=2, bumpy=0.3):
    """A billowy mass: many rough lumps gathered near the surface of a squashed ball."""
    rnd = random.Random(seed); bm = bmesh.new()
    for i in range(n):
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized() * rnd.uniform(0.45, 1.0)
        c = Vector((d.x * radius * stretch[0], d.y * radius * stretch[1], d.z * radius * squash * stretch[2])); r = radius * rnd.uniform(*lump)
        res = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
        off = Vector((seed + i * 1.3, i * 0.7, seed * 2.1))
        for v in res["verts"]:
            dd = v.co.normalized(); v.co = c + dd * r * (1 + bumpy * noise.noise(dd * 1.8 + off))
    return _obj(name, bm, material, centre)

def _resample(points, m):
    """m points evenly spaced along a polyline of (px, py, d)."""
    seg = [math.dist(a[:2], b[:2]) for a, b in zip(points, points[1:])]; total = sum(seg); out = []
    for i in range(m):
        t = i / (m - 1) * total; k = 0
        while k < len(seg) - 1 and t > seg[k]: t -= seg[k]; k += 1
        f = t / seg[k] if seg[k] else 0; a, b = points[k], points[k + 1]
        out.append(tuple(a[j] + (b[j] - a[j]) * f for j in range(3)))
    return out

def _ridged(p):
    return 1 - 2 * abs(noise.noise(p))

def cliff(name, lip, base, material, back=20.0, rise=0.0, rough=1.0, cols=170, rows=64, seed=0):
    """A rock mass traced from the reference: `lip` is its top edge and `base` where its face
    ends, both as (px, py, distance). The face is lofted between them; the top runs back from the lip."""
    lip_w = [P(*p) for p in _resample(lip, cols)]; base_w = [P(*p) for p in _resample(base, cols)]
    bm = bmesh.new(); off = Vector((seed * 3.1, seed * 1.7, seed)); grid = []
    back_rows = 6
    for r in range(-back_rows, rows + 1):
        row = []
        for c in range(cols):
            away = (lip_w[c] - CAM.location); away.z = 0; away.normalize()
            if r <= 0:      # the top, running away from the camera
                s = -r / back_rows; p = lip_w[c] + away * back * s + Vector((0, 0, rise * s))
                p.z += 0.02 * back * noise.noise(p * 0.05 + off) * s
            else:           # the face
                t = r / rows; p = lip_w[c].lerp(base_w[c], t)
                scale = (lip_w[c] - CAM.location).length * 0.06 * rough
                q = Vector((p.x, p.y, p.z * 0.3)) / scale      # squashed in z: fractures run vertically
                bulge = 1.3 * _ridged(q * 0.35 + off) + 0.7 * _ridged(q * 0.9 + off * 2) + 0.35 * noise.noise(q * 2.4 + off) + 0.25 * math.sin(p.z / scale * 3.0 + 4 * noise.noise(q * 0.3))
                p = p - away * scale * (bulge + 0.6) * min(1.0, t * 6) ** 0.7
            row.append(bm.verts.new(p))
        grid.append(row)
    for a, b in zip(grid, grid[1:]):
        for c in range(cols - 1): bm.faces.new((a[c], a[c + 1], b[c + 1], b[c]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _obj(name, bm, material)
    # normals must face the camera side
    if sum((f.normal.dot(CAM.location - f.center) > 0) for f in o.data.polygons) < len(o.data.polygons) / 2: o.data.flip_normals()
    o.data.set_sharp_from_angle(angle=math.radians(32))
    return o

def fog(density, colour, size=(2400, 2000, 1400), at=(0, 800, -200), anisotropy=0.4):
    m = bpy.data.materials.new("fog"); nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    v = nt.nodes.new("ShaderNodeVolumeScatter"); v.inputs["Color"].default_value = (*colour, 1); v.inputs["Density"].default_value = density; v.inputs["Anisotropy"].default_value = anisotropy
    nt.links.new(v.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Volume"])
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(at) @ Matrix.Diagonal((*size, 1)))
    return _obj("fog", bm, m, smooth=False)

def light(sun_dir, sun_energy, sun_colour, sky_colour, sky_strength):
    w = bpy.data.worlds.new("w"); scene.world = w; bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*sky_colour, 1); bg.inputs["Strength"].default_value = sky_strength
    s = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); s.data.energy, s.data.color, s.data.angle = sun_energy, sun_colour, math.radians(2)
    s.rotation_euler = Vector(sun_dir).to_track_quat("-Z", "Y").to_euler(); scene.collection.objects.link(s)

def render(path, width, samples):
    scene.render.engine = "CYCLES"; scene.cycles.samples = samples; scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4; scene.cycles.volume_bounces = 2; scene.cycles.volume_step_rate = 1.0; scene.cycles.volume_max_steps = 192
    scene.render.resolution_x, scene.render.resolution_y = width, round(width * REF_H / REF_W)
    scene.view_settings.view_transform = "Standard"
    scene.render.filepath = path; bpy.ops.render.render(write_still=True)


# ---- technique 1: leaf-card foliage -------------------------------------------------
def leaf_material(name, shade, mid, light, glint, glow=0.12):
    """Each leaf is one flat colour picked from the mass's soft shading, varied leaf by leaf."""
    m = bpy.data.materials.new(name); nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 1.0
    geo = nt.nodes.new("ShaderNodeNewGeometry"); tc = nt.nodes.new("ShaderNodeTexCoord")
    nrm = nt.nodes.new("ShaderNodeVectorMath"); nrm.operation = "NORMALIZE"; nt.links.new(tc.outputs["Object"], nrm.inputs[0])
    vt = nt.nodes.new("ShaderNodeVectorTransform"); vt.vector_type, vt.convert_from, vt.convert_to = "NORMAL", "OBJECT", "WORLD"; nt.links.new(nrm.outputs[0], vt.inputs[0])
    nt.links.new(vt.outputs[0], bsdf.inputs["Normal"])                    # light the whole mass as one soft ball
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(vt.outputs[0], sep.inputs[0])
    rnd = geo.outputs["Random Per Island"]
    lift = nt.nodes.new("ShaderNodeMath"); lift.operation = "MULTIPLY_ADD"; lift.inputs[1].default_value = 0.45; lift.inputs[2].default_value = -0.22
    nt.links.new(rnd, lift.inputs[0])
    z = nt.nodes.new("ShaderNodeMath"); z.operation = "ADD"; nt.links.new(sep.outputs["Z"], z.inputs[0]); nt.links.new(lift.outputs[0], z.inputs[1])
    col = _ramp(nt, z.outputs[0], [(0.05, shade), (0.5, mid), (0.82, light), (1.02, glint)])
    nt.links.new(col, bsdf.inputs["Base Color"]); nt.links.new(col, bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = glow
    return m

def foliage(name, centre, radius, core_mat, leaf_mat, lumps=60, leaves=45, leaf=0.085, squash=0.8, seed=0, lump=(0.2, 0.36)):
    """A foliage mass: a dark core of lumps, covered in thousands of small leaf cards that break up its outline."""
    rnd = random.Random(seed); core = bmesh.new(); cards = bmesh.new(); size = radius * leaf
    for i in range(lumps):
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized() * rnd.uniform(0.4, 1.0)
        c = Vector((d.x * radius, d.y * radius, d.z * radius * squash)); r = radius * rnd.uniform(*lump)
        res = bmesh.ops.create_icosphere(core, subdivisions=1, radius=1.0)
        for v in res["verts"]: v.co = c + v.co.normalized() * r * 0.82
        for _ in range(leaves):
            n = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
            p = c + n * r * rnd.uniform(0.85, 1.12)
            if p.length < radius * 0.55: continue                       # buried inside the mass
            n = (n + Vector((rnd.uniform(-.6, .6), rnd.uniform(-.6, .6), rnd.uniform(-.6, .6)))).normalized()
            t1 = n.orthogonal().normalized(); t1.rotate(Matrix.Rotation(rnd.uniform(0, math.tau), 3, n)); t2 = n.cross(t1)
            ln, wd = size * rnd.uniform(0.8, 1.7), size * rnd.uniform(0.45, 0.8)
            cards.faces.new([cards.verts.new(p + t1 * ln), cards.verts.new(p + t2 * wd), cards.verts.new(p - t1 * ln * 0.7), cards.verts.new(p - t2 * wd)])
    _obj(name + "_core", core, core_mat, centre)
    return _obj(name, cards, leaf_mat, centre, smooth=False)

def flat_material(name, colour):
    m = bpy.data.materials.new(name); b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*srgb(colour), 1); b.inputs["Roughness"].default_value = 1.0
    return m

# ---- technique 2: volumetric cloud ---------------------------------------------------
def cloud(name, centre, radius, density=1.0, seed=0, squash=0.5, stretch=1.5, wisp=0.55, emit=0.11, edge=0.0, colour=(0.8, 0.9, 1.0)):
    """A cloud: a lumpy shell filled with scattering, thinned by noise so its edges go wispy."""
    o = puff(name, centre, radius, flat_material("tmp", "#ffffff"), n=22, squash=squash, seed=seed, lump=(0.45, 0.75), stretch=(stretch, stretch, 1), subdiv=2, bumpy=0.25)
    m = bpy.data.materials.new(name); nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord"); no = nt.nodes.new("ShaderNodeTexNoise")
    no.inputs["Scale"].default_value = 2.2 / radius; no.inputs["Detail"].default_value = 7; no.inputs["Roughness"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], no.inputs["Vector"])
    # fade toward the outside of the whole mass so the lump shells never show as hard outlines
    ext = 1.6 * radius; sm = nt.nodes.new("ShaderNodeVectorMath"); sm.operation = "MULTIPLY"; sm.inputs[1].default_value = (1 / (ext * stretch), 1 / (ext * stretch), 1 / (ext * squash))
    nt.links.new(tc.outputs["Object"], sm.inputs[0]); ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; nt.links.new(sm.outputs[0], ln.inputs[0])
    sq_ = nt.nodes.new("ShaderNodeMath"); sq_.operation = "MULTIPLY"; nt.links.new(ln.outputs["Value"], sq_.inputs[0]); nt.links.new(ln.outputs["Value"], sq_.inputs[1])
    sub = nt.nodes.new("ShaderNodeMath"); sub.operation = "MULTIPLY_ADD"; sub.inputs[1].default_value = -edge; nt.links.new(sq_.outputs[0], sub.inputs[0]); nt.links.new(no.outputs[0], sub.inputs[2])
    dens = _ramp(nt, sub.outputs[0], [(wisp - 0.12, (0, 0, 0)), (wisp + 0.16, (1, 1, 1))])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = density * 2.6 / radius; nt.links.new(dens, mul.inputs[0])
    sc = nt.nodes.new("ShaderNodeVolumeScatter"); sc.inputs["Color"].default_value = (*[min(1.0, c * 1.15) for c in colour], 1); sc.inputs["Anisotropy"].default_value = 0.5
    nt.links.new(mul.outputs[0], sc.inputs["Density"])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*colour, 1)      # stands in for light bounced around inside
    es = nt.nodes.new("ShaderNodeMath"); es.operation = "MULTIPLY"; es.inputs[1].default_value = emit; nt.links.new(mul.outputs[0], es.inputs[0]); nt.links.new(es.outputs[0], em.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(sc.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Volume"])
    o.data.materials.clear(); o.data.materials.append(m)
    return o

# ---- technique 3: light shafts ---------------------------------------------------------
def gobo(sun_dir, target, spread, count=14, seed=0, size=(18, 60)):
    """Out-of-frame shapes between the sun and the scene, so the fog shows shafts of light and shadow."""
    rnd = random.Random(seed); up = -Vector(sun_dir).normalized(); side = up.orthogonal().normalized(); fwd = up.cross(side); m = flat_material("gobo", "#000000")
    for i in range(count):
        c = Vector(target) + up * rnd.uniform(500, 650) + side * rnd.uniform(-spread, spread) + fwd * rnd.uniform(-spread, spread)
        o = puff("gobo", c, rnd.uniform(*size), m, n=8, seed=seed + i, subdiv=1)
        o.visible_camera = False

def shafts(sun_dir, points, length=520, width=(5, 15), strength=0.0007, colour=(1.0, 0.97, 0.85), seed=0):
    """Light shafts, placed by hand: faint glowing beams along the sun's direction through the given points."""
    rnd = random.Random(seed); d = Vector(sun_dir).normalized(); side = d.cross(Vector((0, 1, 0))).normalized(); depth = d.cross(side)
    m = bpy.data.materials.new("shaft"); nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    # brightest along the beam's centre line, fading to nothing at its sides
    edge = _ramp(nt, sep.outputs["X"], [(0.0, (0, 0, 0)), (0.5, (1, 1, 1)), (1.0, (0, 0, 0))])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = strength; nt.links.new(edge, mul.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*colour, 1); nt.links.new(mul.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Volume"])
    for p in points:
        w = rnd.uniform(*width); bm = bmesh.new()
        basis = Matrix((side, d, depth)).transposed().to_4x4()
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(Vector(p) - d * length * 0.1) @ basis @ Matrix.Diagonal((w, length, 26, 1)))
        _obj("shaft", bm, m, smooth=False)


# ---- added for scene 4 ---------------------------------------------------------------
def px_radius(px, py, d, w):
    """World length of w reference pixels at pixel (px, py), d metres away."""
    return (P(px + w, py, d) - P(px, py, d)).length

def pillar(name, spine, material, segs=56, rings=110, rough=1.0, seed=0, cap=True):
    """A free-standing rock column traced from the reference. `spine` is a list of
    (px, py, d, half_width_px) down its centre line, top first. Craggy, with vertical flutes."""
    off = Vector((seed * 2.3, seed * 1.1, seed * 0.7)); bm = bmesh.new(); grid = []
    # resample the spine evenly
    pts = _resample([s[:3] for s in spine], rings); seg = [math.dist(a[:2], b[:2]) for a, b in zip(spine, spine[1:])]; total = sum(seg)
    def width(t):
        t *= total; k = 0
        while k < len(seg) - 1 and t > seg[k]: t -= seg[k]; k += 1
        f = t / seg[k] if seg[k] else 0; return spine[k][3] + (spine[k + 1][3] - spine[k][3]) * f
    for i, p in enumerate(pts):
        t = i / (rings - 1); c = P(*p); r = px_radius(p[0], p[1], p[2], width(t))
        if cap: r *= min(1.0, 0.25 + (t * 28) ** 0.5)          # rounded crown
        row = []
        for j in range(segs):
            a = j / segs * math.tau; dv = Vector((math.cos(a), math.sin(a), 0))
            q = Vector((dv.x * 2.2, dv.y * 2.2, c.z / max(r, 0.01) * 0.10))
            k = 1 + rough * (0.16 * _ridged(q * 1.1 + off) + 0.10 * _ridged(q * 2.6 + off * 2) + 0.05 * noise.noise(Vector((dv.x * 6, dv.y * 6, c.z / max(r, 0.01) * 0.9)) + off))
            row.append(bm.verts.new(c + dv * r * k))
        grid.append(row)
    for a, b in zip(grid, grid[1:]):
        for j in range(segs): bm.faces.new((a[j], a[(j + 1) % segs], b[(j + 1) % segs], b[j]))
    if cap: bm.faces.new(grid[0])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _obj(name, bm, material)
    o.data.set_sharp_from_angle(angle=math.radians(35))
    return o

def clumps(name, items, core_mat, leaf_mat, seed=0, lumps=45, leaves=80, leaf=0.09, squash=0.8, lump=(0.2, 0.36)):
    """Many foliage masses from a list of (px, py, d, radius_m[, squash])."""
    for i, it in enumerate(items):
        foliage(name, P(*it[:3]), it[3], core_mat, leaf_mat, lumps=lumps, leaves=leaves, leaf=leaf, squash=it[4] if len(it) > 4 else squash, seed=seed + i, lump=lump)


# ---- added for scene 3 (inverted forest) ---------------------------------------------
def _catmull(pts, n):
    """n points along a smooth curve through pts (tuples of equal length)."""
    k = len(pts); out = []
    for i in range(n):
        x = i / (n - 1) * (k - 1); a = min(int(x), k - 2); f = x - a
        p0, p1, p2, p3 = pts[max(a - 1, 0)], pts[a], pts[a + 1], pts[min(a + 2, k - 1)]
        out.append(tuple(0.5 * (2 * p1[j] + (p2[j] - p0[j]) * f + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * f * f + (3 * p1[j] - p0[j] - 3 * p2[j] + p3[j]) * f ** 3) for j in range(len(p1))))
    return out

def _set_uv(o, uvs):
    """uvs: one list of (u, v) per polygon, in loop order."""
    layer = o.data.uv_layers.new(name="uv")
    for poly, pu in zip(o.data.polygons, uvs):
        for li, uv in zip(poly.loop_indices, pu): layer.data[li].uv = uv

def uv_material(name, cols, vcols=None, uscale=10.0, vscale=1.0, ribs=0, bands=0, bump=0.6, crease=0.45, vmix=(0.3, 0.8), glow=0.0):
    """Streaked surface painted along a mesh's own UVs (u across, v along): bark strands, cap ribs.
    `vcols` is a second colour set blended in toward v=1; `ribs`/`bands` darken creases at whole numbers of u*ribs / v*bands."""
    m = bpy.data.materials.new(name); nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    uv = nt.nodes.new("ShaderNodeUVMap"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (uscale, vscale, 1); nt.links.new(uv.outputs[0], mp.inputs[0])
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 1.0; n1.inputs["Detail"].default_value = 7; n1.inputs["Roughness"].default_value = 0.62; nt.links.new(mp.outputs[0], n1.inputs["Vector"])
    col = _ramp(nt, n1.outputs[0], [(0.3, cols[0]), (0.52, cols[1]), (0.75, cols[2])])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(uv.outputs[0], sep.inputs[0])
    if vcols:
        col2 = _ramp(nt, n1.outputs[0], [(0.3, vcols[0]), (0.52, vcols[1]), (0.75, vcols[2])])
        jit = nt.nodes.new("ShaderNodeMath"); jit.operation = "MULTIPLY_ADD"; jit.inputs[1].default_value = 0.5; jit.inputs[2].default_value = -0.25; nt.links.new(n1.outputs[0], jit.inputs[0])
        vv = nt.nodes.new("ShaderNodeMath"); vv.operation = "ADD"; nt.links.new(sep.outputs["Y"], vv.inputs[0]); nt.links.new(jit.outputs[0], vv.inputs[1])
        col = _mix(nt, "MIX", _ramp(nt, vv.outputs[0], [(vmix[0], (0, 0, 0)), (vmix[1], (1, 1, 1))]), col, col2)
    for count, chan in ((ribs, "X"), (bands, "Y")):
        if not count: continue
        mu = nt.nodes.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = count; nt.links.new(sep.outputs[chan], mu.inputs[0])
        if chan == "Y" and ribs:      # each rib's bands start at a different place, like overlapping feathers
            ru = nt.nodes.new("ShaderNodeMath"); ru.operation = "MULTIPLY"; ru.inputs[1].default_value = ribs; nt.links.new(sep.outputs["X"], ru.inputs[0])
            fl = nt.nodes.new("ShaderNodeMath"); fl.operation = "FLOOR"; nt.links.new(ru.outputs[0], fl.inputs[0])
            wn = nt.nodes.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "1D"; nt.links.new(fl.outputs[0], wn.inputs["W"])
            ad = nt.nodes.new("ShaderNodeMath"); ad.operation = "ADD"; nt.links.new(mu.outputs[0], ad.inputs[0]); nt.links.new(wn.outputs["Value"], ad.inputs[1]); mu = ad
        fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "FRACT"; nt.links.new(mu.outputs[0], fr.inputs[0])
        k = 1 - crease
        if chan == "X": shade = _ramp(nt, fr.outputs[0], [(0.0, (k, k, k)), (0.22, (1, 1, 1)), (0.78, (1, 1, 1)), (1.0, (k, k, k))])
        else: k = 1 - crease * 0.55; shade = _ramp(nt, fr.outputs[0], [(0.0, (k, k, k)), (0.6, (1, 1, 1)), (0.86, (1, 1, 1)), (0.97, (1.3, 1.3, 1.25))])
        col = _mix(nt, "MULTIPLY", 1.0, col, shade)
    nt.links.new(col, bsdf.inputs["Base Color"])
    if glow:
        nt.links.new(col, bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = glow
    mp2 = nt.nodes.new("ShaderNodeMapping"); mp2.inputs["Scale"].default_value = (uscale * 2.5, vscale * 2.5, 1); nt.links.new(uv.outputs[0], mp2.inputs[0])
    n3 = nt.nodes.new("ShaderNodeTexNoise"); n3.inputs["Scale"].default_value = 1.0; n3.inputs["Detail"].default_value = 9; nt.links.new(mp2.outputs[0], n3.inputs["Vector"])
    bn = nt.nodes.new("ShaderNodeBump"); bn.inputs["Strength"].default_value = bump; nt.links.new(n3.outputs[0], bn.inputs["Height"]); nt.links.new(bn.outputs[0], bsdf.inputs["Normal"])
    return m

def trunk(name, spine, material, strands=4, twist=1.5, spread=0.5, thick=0.62, segs=14, rings=90, seed=0, wobble=0.25):
    """A twisted trunk traced from the reference: a bundle of `strands` ropes winding `twist` turns
    around a smooth curve through `spine` = (px, py, d, half_width_px). strands=1 gives a plain stem."""
    rnd = random.Random(seed); pts = _catmull(spine, rings)
    cs = [P(*p[:3]) for p in pts]; rs = [px_radius(p[0], p[1], p[2], max(p[3], 0.2)) for p in pts]
    # parallel-transported frames
    tans = [(cs[min(i + 1, rings - 1)] - cs[max(i - 1, 0)]).normalized() for i in range(rings)]
    nrm = tans[0].orthogonal().normalized(); frames = []
    for t in tans:
        nrm = (nrm - t * nrm.dot(t)).normalized(); frames.append((nrm, t.cross(nrm)))
    length = [0.0]
    for a, b in zip(cs, cs[1:]): length.append(length[-1] + (b - a).length)
    bm = bmesh.new(); uvs = []
    for k in range(strands):
        ph0 = k / strands * math.tau + rnd.uniform(-0.3, 0.3); off = spread if strands > 1 else 0.0
        sr = thick * rnd.uniform(0.8, 1.15) if strands > 1 else 1.0; so = Vector((seed * 1.7 + k * 5.1, k * 2.3, seed)); grid = []
        tw = twist * rnd.uniform(0.8, 1.2)
        for i in range(rings):
            t = i / (rings - 1); n, b = frames[i]; r = rs[i]
            ph = ph0 + tw * math.tau * t + wobble * 3 * noise.noise(Vector((t * 3, k, seed)))
            c = cs[i] + (n * math.cos(ph) + b * math.sin(ph)) * r * off * (1 + wobble * noise.noise(Vector((t * 4, k * 3.3, seed + 9))))
            row = []
            for j in range(segs):
                a = j / segs * math.tau; dv = n * math.cos(a) + b * math.sin(a)
                q = Vector((math.cos(a) * 1.6, math.sin(a) * 1.6, length[i] / max(r, 0.01) * 0.12)) + so
                kk = 1 + 0.16 * _ridged(q) + 0.08 * noise.noise(q * 2.7)
                row.append(bm.verts.new(c + dv * r * sr * kk))
            grid.append(row)
        for i in range(rings - 1):
            for j in range(segs):
                j2 = (j + 1) % segs; bm.faces.new((grid[i][j], grid[i][j2], grid[i + 1][j2], grid[i + 1][j]))
                u0, u1 = j / segs + k * 0.37, (j + 1) / segs + k * 0.37; v0, v1 = length[i] / 4, length[i + 1] / 4
                uvs.append([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _obj(name, bm, material); _set_uv(o, uvs)
    return o

def cap(name, hub, centre, A, B, material, top_material, normal=(0, 0, 1), yaw=0.0, ribs=24, rib_amp=0.05, shingles=5, shingle_amp=0.04,
        round_=1.8, ragged=0.1, swirl=0.0, lift=None, segs=192, rings=40, seed=0, mound=0.12, dish=0.12, spread_pow=0.8, rib_jitter=0.7, shingle_jitter=0.5):
    """An upturned mushroom-cap / giant-leaf platform. `hub` is its lowest point (world), `centre` the middle of
    its rim (world), A and B the rim radii in metres across and in depth, `normal` the rim plane's up direction.
    The underside is ribbed and shingled like overlapping feathers; the top is a lumpy mossy mound.
    `lift(angle)` adds height round the rim (angle 0 = +u/right, 3pi/2 = toward the camera when yaw=0)."""
    n = Vector(normal).normalized(); u = (Vector((1, 0, 0)) - n * n.x).normalized(); u.rotate(Matrix.Rotation(yaw, 3, n)); v = n.cross(u)
    hub, centre = Vector(hub), Vector(centre); R = (A + B) / 2; so = Vector((seed * 3.3, seed * 1.9, seed * 0.7))
    bm = bmesh.new(); uvs = []; grid = []; rims = []
    phs = [j / segs * ribs + rib_jitter * noise.noise(Vector((math.cos(j / segs * math.tau) * ribs * 0.08, math.sin(j / segs * math.tau) * ribs * 0.08, 7)) + so) for j in range(segs)] + [ribs]
    for j in range(segs):
        a = j / segs * math.tau; ca, sa = math.cos(a), math.sin(a)
        rr = 1 + ragged * (0.7 * noise.noise(Vector((ca * 1.2, sa * 1.2, 0)) + so) + 0.5 * noise.noise(Vector((ca * 4, sa * 4, 3)) + so) + 0.3 * abs(math.sin(math.pi * phs[j])) * (0.4 + noise.noise(Vector((math.floor(phs[j]) * 0.9, 2, 5)) + so)))
        rim = centre + (u * ca * A + v * sa * B) * rr + n * (lift(a) if lift else 0.0); rims.append(rim)
        rel = rim - hub; h = rel.dot(n); lat = rel - n * h; outward = (lat.normalized() * 0.5 - n).normalized(); col = []
        for i in range(rings + 1):
            t = 0.03 + 0.97 * i / rings; ph = phs[j] + swirl * t
            rib = abs(math.sin(math.pi * ph)) ** 0.5
            sh = (t * shingles + (math.sin(math.floor(ph) * 12.9898 + seed) * 43758.5453) % 1.0 + shingle_jitter * noise.noise(Vector((ph * 0.7, t * 2, 1)) + so)) % 1.0
            p = hub + lat * t ** spread_pow + n * h * t ** round_ + outward * R * (rib_amp * rib + shingle_amp * sh * (1 - t) ** 0.3) * min(1.0, t * 4)
            col.append(bm.verts.new(p))
        grid.append(col)
    under = []
    for j in range(segs):
        j2 = (j + 1) % segs
        for i in range(rings):
            under.append(bm.faces.new((grid[j][i], grid[j2][i], grid[j2][i + 1], grid[j][i + 1])))
            ua, ub = phs[j] / ribs, (phs[j + 1] if j + 1 < segs else phs[0] + ribs) / ribs; s0, s1 = swirl * (0.03 + 0.97 * i / rings) / ribs, swirl * (0.03 + 0.97 * (i + 1) / rings) / ribs
            uvs.append([(ua + s0, i / rings), (ub + s0, i / rings), (ub + s1, (i + 1) / rings), (ua + s1, (i + 1) / rings)])
    f = bm.faces.new([grid[j][0] for j in range(segs)]); uvs.append([(0, 0)] * segs)
    # the top: a lumpy mound running in from the rim
    m = 14; tops = [[grid[j][rings] for j in range(segs)]]; ctop = centre + n * ((sum(lift(j / segs * math.tau) for j in range(segs)) / segs) if lift else 0.0)
    for k in range(1, m):
        s = k / m; row = []
        for j in range(segs):
            p = rims[j].lerp(ctop, s)
            lump = 0.3 + 1.3 * abs(noise.noise(p * (5.0 / R) + so)) + 0.6 * abs(noise.noise(p * (11.0 / R) + so))
            row.append(bm.verts.new(p + n * R * (mound * lump * min(1.0, s * 5) ** 0.5 * (1 - 0.6 * s) - dish * s)))
        tops.append(row)
    topf = []
    for a_, b_ in zip(tops, tops[1:]):
        for j in range(segs):
            j2 = (j + 1) % segs; topf.append(bm.faces.new((a_[j], b_[j], b_[j2], a_[j2]))); uvs.append([(0, 0)] * 4)
    topf.append(bm.faces.new(list(reversed(tops[-1])))); uvs.append([(0, 0)] * segs)
    for fc in topf: fc.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _obj(name, bm, material); o.data.materials.append(top_material); _set_uv(o, uvs)
    global LAST_RIM; LAST_RIM = (rims, n)      # world rim points and up direction, for draping growth along the rim
    return o

def sky(stops, strength=1.0, lo=-0.3, hi=0.3):
    """Replace the flat world colour with a vertical gradient: stops are (0..1, colour) from `lo` to `hi` in view-direction z."""
    nt = scene.world.node_tree; bg = nt.nodes["Background"]; tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value, mr.inputs[2].default_value = lo, hi; nt.links.new(sep.outputs["Z"], mr.inputs[0])
    nt.links.new(_ramp(nt, mr.outputs[0], stops), bg.inputs["Color"]); bg.inputs["Strength"].default_value = strength

def preview(path, scale=2):
    """Layout check without rendering: splat every mesh vertex at its reference pixel, nearest on top, one colour per object."""
    import numpy as np
    W, H = int(REF_W * scale), int(REF_H * scale); img = np.full((H, W, 3), 40, np.uint8); zb = np.full((H, W), 1e9)
    half_w = 18.0 / CAM.data.lens; half_h = half_w * REF_H / REF_W; inv = CAM.matrix_world.inverted(); rnd = random.Random(1)
    for o in scene.collection.objects:
        if o.type != "MESH" or not o.visible_camera or o.name.startswith(("fog", "cloud", "shaft")): continue
        colr = [rnd.randint(70, 255) for _ in range(3)]; mw = inv @ o.matrix_world
        co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        M = np.array(mw); pc = co @ M[:3, :3].T + M[:3, 3]; z = -pc[:, 2]; ok = z > 0.1
        x = ((pc[:, 0] / np.maximum(z, 0.1) / half_w + 1) * W / 2).astype(int); y = ((1 - pc[:, 1] / np.maximum(z, 0.1) / half_h) * H / 2).astype(int)
        ok &= (x >= 1) & (x < W - 1) & (y >= 1) & (y < H - 1)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                xs, ys, zs = x[ok] + dx, y[ok] + dy, z[ok]; order = np.argsort(-zs); xs, ys, zs = xs[order], ys[order], zs[order]
                near = zs < zb[ys, xs]; img[ys[near], xs[near]] = colr; zb[ys[near], xs[near]] = zs[near]
    with open(path, "wb") as fh: fh.write(b"P6 %d %d 255\n" % (W, H)); fh.write(img.tobytes())

def haze(density, stops, z_lo, z_hi, size=(400, 300, 300), at=(0, 160, 0)):
    """Painted depth haze that ignores the lighting: a box that absorbs and glows at the same rate, so anything
    seen through it fades toward a chosen colour. The colour is a ramp over world height z_lo..z_hi (stops as 0..1, colour),
    e.g. warm cloud-glow below and cool dusk above. Start the box behind the nearest masses."""
    m = bpy.data.materials.new("haze"); nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value, mr.inputs[2].default_value = z_lo, z_hi; nt.links.new(sep.outputs["Z"], mr.inputs[0])
    ab = nt.nodes.new("ShaderNodeVolumeAbsorption"); ab.inputs["Color"].default_value = (0, 0, 0, 1); ab.inputs["Density"].default_value = density
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = density; nt.links.new(_ramp(nt, mr.outputs[0], stops), em.inputs["Color"])
    add = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(ab.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Volume"])
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(at) @ Matrix.Diagonal((*size, 1)))
    return _obj("fog_haze", bm, m, smooth=False)

def backdrop_haze(density, stops, lo=-0.25, hi=0.25, cloud=0.5, cloud_scale=7.0, size=(600, 400, 400), at=(0, 209, 0)):
    """Depth haze that fades everything toward a painted backdrop. Like `haze`, but the colour depends on the view
    direction, not on position: `stops` are (0..1, dark colour, light colour) from looking down (`lo`) to up (`hi`),
    and a cloud-shaped noise fixed to the view picks between dark and light, so the far distance reads as painted cloud banks."""
    m = bpy.data.materials.new("bhaze"); nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Incoming"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value, mr.inputs[2].default_value = -lo, -hi; nt.links.new(sep.outputs["Z"], mr.inputs[0])
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (cloud_scale, cloud_scale, cloud_scale * 2.6); nt.links.new(geo.outputs["Incoming"], mp.inputs[0])
    no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 1.0; no.inputs["Detail"].default_value = 6; no.inputs["Roughness"].default_value = 0.55; no.inputs["Distortion"].default_value = 0.6
    nt.links.new(mp.outputs[0], no.inputs["Vector"])
    puff_ = _ramp(nt, no.outputs[0], [(0.5 - cloud * 0.3, (0, 0, 0)), (0.5 + cloud * 0.3, (1, 1, 1))])
    dark = _ramp(nt, mr.outputs[0], [(p, a) for p, a, b in stops]); lite = _ramp(nt, mr.outputs[0], [(p, b) for p, a, b in stops])
    col = _mix(nt, "MIX", puff_, dark, lite)
    ab = nt.nodes.new("ShaderNodeVolumeAbsorption"); ab.inputs["Color"].default_value = (0, 0, 0, 1); ab.inputs["Density"].default_value = density
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = density; nt.links.new(col, em.inputs["Color"])
    add = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(ab.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Volume"])
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(at) @ Matrix.Diagonal((*size, 1)))
    return _obj("fog_bhaze", bm, m, smooth=False)
