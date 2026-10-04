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

def rock_material(name, rock=("#2e2a2b", "#5b5352", "#8a7d76"), grass=("#3f8f2a", "#7fd036"), streak=1.0, grass_from=0.62, patch=None, moss=None, patch_scale=0.02):
    """Rock on steep faces, with vertical streaks; grass wherever the surface faces up."""
    m = bpy.data.materials.new(name); nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 1.0
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mp = nt.nodes.new("ShaderNodeMapping"); nt.links.new(geo.outputs["Position"], mp.inputs[0]); mp.inputs["Scale"].default_value = (0.09, 0.09, 0.012)
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

def cliff(name, lip, base, material, back=20.0, rise=0.0, rough=1.0, cols=170, rows=64, seed=0, strata=0.25):
    """A rock mass traced from the reference: `lip` is its top edge and `base` where its face
    ends, both as (px, py, distance). The face is lofted between them; the top runs back from the lip."""
    if isinstance(lip[0], Vector):   # world-space polylines
        lip_w = [Vector(p) for p in _resample([tuple(p) for p in lip], cols)]; base_w = [Vector(p) for p in _resample([tuple(p) for p in base], cols)]
    else:
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
                bulge = 1.3 * _ridged(q * 0.35 + off) + 0.7 * _ridged(q * 0.9 + off * 2) + 0.35 * noise.noise(q * 2.4 + off) + strata * math.sin(p.z / scale * 3.0 + 4 * noise.noise(q * 0.3))
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
    scene.cycles.max_bounces = 4; scene.cycles.volume_bounces = 4; scene.cycles.volume_step_rate = 1.0; scene.cycles.volume_max_steps = 192
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
def cloud(name, centre, radius, density=1.0, seed=0, squash=0.5, stretch=1.5, wisp=0.55, n=22, lump=(0.45, 0.75), emit=0.11, nscale=2.2, bumpy=0.25, emit_colour=(0.8, 0.9, 1.0)):
    """A cloud: a lumpy shell filled with scattering, thinned by noise so its edges go wispy."""
    o = puff(name, centre, radius, flat_material("tmp", "#ffffff"), n=n, squash=squash, seed=seed, lump=lump, stretch=(stretch, stretch, 1), subdiv=2, bumpy=bumpy)
    m = bpy.data.materials.new(name); nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord"); no = nt.nodes.new("ShaderNodeTexNoise")
    no.inputs["Scale"].default_value = nscale / radius; no.inputs["Detail"].default_value = 7; no.inputs["Roughness"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], no.inputs["Vector"])
    dens = _ramp(nt, no.outputs[0], [(wisp - 0.12, (0, 0, 0)), (wisp + 0.16, (1, 1, 1))])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = density * 2.6 / radius; nt.links.new(dens, mul.inputs[0])
    sc = nt.nodes.new("ShaderNodeVolumeScatter"); sc.inputs["Color"].default_value = (1, 1, 1, 1); sc.inputs["Anisotropy"].default_value = 0.5
    nt.links.new(mul.outputs[0], sc.inputs["Density"])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*emit_colour, 1)      # stands in for light bounced around inside
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


# ---- scene 8 additions ------------------------------------------------------------------
def Z(px, py, z):
    """World point where the ray through reference pixel (px, py) meets the horizontal plane at height z."""
    d = P(px, py, 1.0) - CAM.location
    return CAM.location + d * ((z - CAM.location.z) / d.z)

def grass_material(name, dark, mid, light, scale=0.15, bump=0.6):
    """Painted grass: three greens in soft blotches, with fine mottling."""
    m = bpy.data.materials.new(name); nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 1.0
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = scale; n1.inputs["Detail"].default_value = 6; n1.inputs["Roughness"].default_value = 0.7
    nt.links.new(geo.outputs["Position"], n1.inputs["Vector"])
    col = _ramp(nt, n1.outputs[0], [(0.32, dark), (0.5, mid), (0.68, light)])
    nt.links.new(col, bsdf.inputs["Base Color"])
    n3 = nt.nodes.new("ShaderNodeTexNoise"); n3.inputs["Scale"].default_value = scale * 9; n3.inputs["Detail"].default_value = 6; nt.links.new(geo.outputs["Position"], n3.inputs["Vector"])
    b = nt.nodes.new("ShaderNodeBump"); b.inputs["Strength"].default_value = bump; b.inputs["Distance"].default_value = 0.5
    nt.links.new(n3.outputs[0], b.inputs["Height"]); nt.links.new(b.outputs[0], bsdf.inputs["Normal"])
    return m

def canopy_material(name, light, dark, wall_dark, wall_light, pit, r_in, r_out, z_pit, blotch=0.03, cover=0.56):
    """Forest canopy seen from far above, in the object space of a basin floor centred on a hole:
    light green with dark blotches; radial streaks of trees on the funnel wall; dark pit below z_pit."""
    m = bpy.data.materials.new(name); nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 1.0
    tc = nt.nodes.new("ShaderNodeTexCoord"); pos = tc.outputs["Object"]
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = blotch; n1.inputs["Detail"].default_value = 5; n1.inputs["Roughness"].default_value = 0.62
    nt.links.new(pos, n1.inputs["Vector"])
    big = nt.nodes.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = blotch * 0.2; big.inputs["Detail"].default_value = 2; nt.links.new(pos, big.inputs["Vector"])
    s = nt.nodes.new("ShaderNodeMath"); s.operation = "MULTIPLY_ADD"; s.inputs[1].default_value = 0.25; s.inputs[2].default_value = -0.125; nt.links.new(big.outputs[0], s.inputs[0])
    a = nt.nodes.new("ShaderNodeMath"); a.operation = "ADD"; nt.links.new(n1.outputs[0], a.inputs[0]); nt.links.new(s.outputs[0], a.inputs[1])
    canopy = _ramp(nt, a.outputs[0], [(cover, light), (cover + 0.025, dark)])
    # radial streaks
    flat = nt.nodes.new("ShaderNodeVectorMath"); flat.operation = "MULTIPLY"; flat.inputs[1].default_value = (1, 1, 0); nt.links.new(pos, flat.inputs[0])
    ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; nt.links.new(flat.outputs[0], ln.inputs[0]); r = ln.outputs["Value"]
    nrm = nt.nodes.new("ShaderNodeVectorMath"); nrm.operation = "NORMALIZE"; nt.links.new(flat.outputs[0], nrm.inputs[0])
    sc = nt.nodes.new("ShaderNodeVectorMath"); sc.operation = "SCALE"; sc.inputs["Scale"].default_value = 16.0; nt.links.new(nrm.outputs[0], sc.inputs[0])
    rz = nt.nodes.new("ShaderNodeMath"); rz.operation = "MULTIPLY"; rz.inputs[1].default_value = 0.012; nt.links.new(r, rz.inputs[0])
    cz = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(rz.outputs[0], cz.inputs["Z"])
    av = nt.nodes.new("ShaderNodeVectorMath"); av.operation = "ADD"; nt.links.new(sc.outputs[0], av.inputs[0]); nt.links.new(cz.outputs[0], av.inputs[1])
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 1.0; n2.inputs["Detail"].default_value = 3; nt.links.new(av.outputs[0], n2.inputs["Vector"])
    streak = _ramp(nt, n2.outputs[0], [(0.47, wall_dark), (0.53, wall_light)])
    rmask = _ramp(nt, r, [(0.0, (1, 1, 1)), (1.0, (0, 0, 0))])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = r_in; mr.inputs[2].default_value = r_out; nt.links.new(r, mr.inputs[0])
    jit = nt.nodes.new("ShaderNodeMath"); jit.operation = "MULTIPLY_ADD"; jit.inputs[1].default_value = 0.9; jit.inputs[2].default_value = -0.45; nt.links.new(n1.outputs[0], jit.inputs[0])
    ja = nt.nodes.new("ShaderNodeMath"); ja.operation = "ADD"; nt.links.new(mr.outputs[0], ja.inputs[0]); nt.links.new(jit.outputs[0], ja.inputs[1])
    rmask = _ramp(nt, ja.outputs[0], [(0.35, (1, 1, 1)), (0.6, (0, 0, 0))])
    col = _mix(nt, "MIX", rmask, canopy, streak)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(pos, sep.inputs[0])
    zj = nt.nodes.new("ShaderNodeMath"); zj.operation = "MULTIPLY_ADD"; zj.inputs[1].default_value = 60.0; zj.inputs[2].default_value = -30.0; nt.links.new(n2.outputs[0], zj.inputs[0])
    za = nt.nodes.new("ShaderNodeMath"); za.operation = "ADD"; nt.links.new(sep.outputs["Z"], za.inputs[0]); nt.links.new(zj.outputs[0], za.inputs[1])
    pitmask = _ramp(nt, za.outputs[0], [(0.0, (1, 1, 1)), (1.0, (0, 0, 0))])
    mz = nt.nodes.new("ShaderNodeMapRange"); mz.inputs[1].default_value = z_pit * 1.6; mz.inputs[2].default_value = z_pit * 0.6; nt.links.new(za.outputs[0], mz.inputs[0])
    pitmask = _ramp(nt, mz.outputs[0], [(0.0, (1, 1, 1)), (1.0, (0, 0, 0))])
    pc = nt.nodes.new("ShaderNodeRGB"); pc.outputs[0].default_value = (*srgb(pit), 1)
    col = _mix(nt, "MIX", pitmask, col, pc.outputs[0])
    nt.links.new(col, bsdf.inputs["Base Color"])
    b = nt.nodes.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.5; b.inputs["Distance"].default_value = 6.0
    nt.links.new(a.outputs[0], b.inputs["Height"]); nt.links.new(b.outputs[0], bsdf.inputs["Normal"])
    return m

def basin_floor(name, centre, material, r_pit=105, r_funnel=215, wall_drop=55, pit_drop=120, r_max=5000, segs=360, seed=0):
    """A flat floor with a funnel-shaped hole at its centre: jagged rim, radial ridges running down into a deep pit."""
    bm = bmesh.new(); radii = [r_funnel * 1.3 * i / 60 for i in range(1, 61)]
    while radii[-1] < r_max: radii.append(radii[-1] * 1.12)
    off = Vector((seed * 2.3, seed, 0)); centre_v = bm.verts.new((0, 0, -wall_drop - pit_drop)); rings = []
    sm = lambda t: t * t * (3 - 2 * t)
    for r in radii:
        ring = []
        for k in range(segs):
            th = math.tau * k / segs; u = Vector((math.cos(th), math.sin(th), 0))
            rp = r_pit * (1 + 0.22 * noise.noise(u * 1.6 + off)); ro = r_funnel * (1 + 0.25 * noise.noise(u * 2.2 + off * 2))
            t = max(0.0, min(1.0, (ro - r) / (ro - rp)))
            z = -wall_drop * sm(t)
            z += 14 * math.sin(math.pi * min(1.0, t * 1.2)) * _ridged(u * 11.0 + Vector((0, 0, r * 0.004)) + off)      # radial ridges
            if r < rp: z -= pit_drop * sm(min(1.0, (rp - r) / rp * 2.5))
            ring.append(bm.verts.new((u.x * r, u.y * r, z)))
        rings.append(ring)
    for k in range(segs): bm.faces.new((centre_v, rings[0][k], rings[0][(k + 1) % segs]))
    for a, b in zip(rings, rings[1:]):
        for k in range(segs): bm.faces.new((a[k], b[k], b[(k + 1) % segs], a[(k + 1) % segs]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, material, centre)

def mesa(name, outline, drop, material, flare=0.5, rough=4.0, rows=10, per_edge=10, seed=0):
    """A flat-topped outcrop: `outline` is a ring of world points (its top edge); a craggy skirt drops from it."""
    bm = bmesh.new(); pts = []
    for a, b in zip(outline, outline[1:] + outline[:1]):
        for i in range(per_edge): pts.append(Vector(a).lerp(Vector(b), i / per_edge))
    c = sum(pts, Vector()) / len(pts); off = Vector((seed * 1.9, seed * 0.7, seed)); rings = []
    for r in range(rows + 1):
        t = r / rows; ring = []
        for p in pts:
            out = (p - c); out.z = 0; out.normalize()
            q = p + out * drop * flare * t + Vector((0, 0, -drop * t))
            q += out * rough * min(1.0, t * 4) * (_ridged(Vector((q.x, q.y, q.z * 0.3)) * 0.08 + off) + 0.5 * noise.noise(q * 0.3 + off))
            ring.append(bm.verts.new(q))
        rings.append(ring)
    n = len(pts); cv = bm.verts.new(c)
    for k in range(n): bm.faces.new((cv, rings[0][k], rings[0][(k + 1) % n]))
    for a, b in zip(rings, rings[1:]):
        for k in range(n): bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _obj(name, bm, material, smooth=True); o.data.set_sharp_from_angle(angle=math.radians(35))
    return o

def strip(name, a, b, wa, wb, colour=(0.9, 0.95, 1.0), emit=1.0):
    """A thin bright strip between two world points (a distant waterfall)."""
    bm = bmesh.new(); side = (Vector(b) - Vector(a)).cross(Vector(a) - CAM.location).normalized()
    bm.faces.new([bm.verts.new(Vector(a) - side * wa), bm.verts.new(Vector(a) + side * wa), bm.verts.new(Vector(b) + side * wb), bm.verts.new(Vector(b) - side * wb)])
    m = bpy.data.materials.new(name); bs = m.node_tree.nodes["Principled BSDF"]; bs.inputs["Base Color"].default_value = (*colour, 1); bs.inputs["Emission Color"].default_value = (*colour, 1); bs.inputs["Emission Strength"].default_value = emit
    o = _obj(name, bm, m, smooth=False); o.visible_shadow = False; return o

def tufts(name, obj, material, count=6000, size=0.5, seed=0, up_min=0.3, keep=None):
    """Scatter small upright grass/leaf cards over the upward-facing faces of a mesh, to give its surface and outline a painted, tufted look."""
    rnd = random.Random(seed); bm = bmesh.new(); me = obj.data; polys = [p for p in me.polygons if p.normal.z > up_min and p.area > 0]
    if not polys: return None
    w = [p.area for p in polys]; mw = obj.matrix_world
    for p in rnd.choices(polys, weights=w, k=count):
        vs = [me.vertices[i].co for i in p.vertices]; a, b = rnd.random(), rnd.random()
        q = vs[0].lerp(vs[1], a).lerp(vs[2].lerp(vs[-1], a), b); q = mw @ q
        if keep and not keep(q): continue
        th = rnd.uniform(0, math.tau); t1 = Vector((math.cos(th), math.sin(th), 0)); s = size * rnd.uniform(0.6, 1.5)
        up = (Vector((rnd.uniform(-.5, .5), rnd.uniform(-.5, .5), 1))).normalized()
        bm.faces.new([bm.verts.new(q - t1 * s * 0.5), bm.verts.new(q + t1 * s * 0.5), bm.verts.new(q + t1 * s * 0.15 + up * s * 1.3), bm.verts.new(q - t1 * s * 0.25 + up * s * 1.1)])
    return _obj(name, bm, material, smooth=False)

def tuft_material(name, colours, glow=0.03):
    """Flat-coloured cards, one colour per card picked at random from `colours`, all lit as if facing straight up."""
    m = bpy.data.materials.new(name); nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 1.0
    geo = nt.nodes.new("ShaderNodeNewGeometry"); n = len(colours)
    col = _ramp(nt, geo.outputs["Random Per Island"], [(i / (n - 1), c) for i, c in enumerate(colours)])
    up = nt.nodes.new("ShaderNodeCombineXYZ"); up.inputs["Z"].default_value = 1.0; nt.links.new(up.outputs[0], bsdf.inputs["Normal"])
    nt.links.new(col, bsdf.inputs["Base Color"]); nt.links.new(col, bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = glow
    return m


# ---- scene 6 additions ------------------------------------------------------------------
import numpy as np

def attr_material(name, emit=0.0, mottle=0.0, mottle_scale=0.05):
    """Surface coloured by the mesh colour attribute 'col' (face or point domain), no specular."""
    m = bpy.data.materials.new(name); nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    a = nt.nodes.new("ShaderNodeAttribute"); a.attribute_name = "col"; col = a.outputs["Color"]
    if mottle:
        geo = nt.nodes.new("ShaderNodeNewGeometry"); n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = mottle_scale; n.inputs["Detail"].default_value = 7; n.inputs["Roughness"].default_value = 0.7
        nt.links.new(geo.outputs["Position"], n.inputs["Vector"])
        g = _ramp(nt, n.outputs[0], [(0.3, (1 - mottle,) * 3), (0.7, (1 + mottle,) * 3)])
        col = _mix(nt, "MULTIPLY", 1.0, col, g)
    nt.links.new(col, bsdf.inputs["Base Color"])
    if emit:
        nt.links.new(col, bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = emit
    return m

def buildings(name, pos, yaw, size, roof_h, roof_col, wall_col, material):
    """Tens of thousands of tiny gabled houses as ONE mesh. pos (N,3) base centres, yaw (N,), size (N,3)=(w,d,h),
    roof_h (N,), roof_col / wall_col (N,3) linear rgb. Colours go to the face attribute 'col'."""
    pos = np.asarray(pos, float); N = len(pos); w, d, h = (np.asarray(size, float)[:, i] / (1 if i == 2 else 2) for i in range(3))
    sink = h * 0.6      # walls run below the base so houses on slopes have no gap
    lx = np.stack([-w, w, w, -w, -w, w, w, -w, np.zeros(N), np.zeros(N)], 1)
    ly = np.stack([-d, -d, d, d, -d, -d, d, d, -d, d], 1)
    lz = np.stack([-sink] * 4 + [h] * 4 + [h + roof_h] * 2, 1)
    c, s = np.cos(yaw)[:, None], np.sin(yaw)[:, None]
    V = np.stack([pos[:, 0:1] + lx * c - ly * s, pos[:, 1:2] + lx * s + ly * c, pos[:, 2:3] + lz], 2).reshape(-1, 3)
    tmpl = [0, 1, 5, 4, 1, 2, 6, 5, 2, 3, 7, 6, 3, 0, 4, 7,  4, 5, 8, 6, 7, 9,  5, 6, 9, 8, 7, 4, 8, 9]   # 4 walls, 2 gables, 2 roof
    tot = [4, 4, 4, 4, 3, 3, 4, 4]
    loops = (np.arange(N)[:, None] * 10 + np.array(tmpl)[None, :]).ravel()
    ltot = np.tile(tot, N); lstart = np.concatenate([[0], np.cumsum(ltot)[:-1]])
    me = bpy.data.meshes.new(name); me.vertices.add(N * 10); me.loops.add(len(loops)); me.polygons.add(N * 8)
    me.vertices.foreach_set("co", V.ravel()); me.loops.foreach_set("vertex_index", loops.astype(np.int32))
    me.polygons.foreach_set("loop_start", lstart.astype(np.int32)); me.polygons.foreach_set("loop_total", ltot.astype(np.int32))
    me.update(calc_edges=True); me.validate()
    rc = np.concatenate([np.asarray(roof_col, float), np.ones((N, 1))], 1); wc = np.concatenate([np.asarray(wall_col, float), np.ones((N, 1))], 1)
    fc = np.stack([wc] * 6 + [rc] * 2, 1).reshape(-1, 4)
    ca = me.color_attributes.new("col", "FLOAT_COLOR", "FACE"); ca.data.foreach_set("color", fc.ravel())
    me.materials.append(material)
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o); return o

def grid_mesh(name, rows, colours, material, closed=True, smooth=True):
    """Mesh from rings of points: rows is a list of equal-length lists of (x,y,z); colours the same shape of rgb.
    Used for a ring-shaped rim terrain plus the inner wall of a pit."""
    R, C = len(rows), len(rows[0]); V = np.array(rows, float).reshape(-1, 3)
    cc = C if closed else C - 1
    r, c = np.meshgrid(np.arange(R - 1), np.arange(cc), indexing="ij"); c2 = (c + 1) % C
    F = np.stack([r * C + c, r * C + c2, (r + 1) * C + c2, (r + 1) * C + c], 2).reshape(-1, 4)
    me = bpy.data.meshes.new(name); me.vertices.add(len(V)); me.loops.add(F.size); me.polygons.add(len(F))
    me.vertices.foreach_set("co", V.ravel()); me.loops.foreach_set("vertex_index", F.ravel().astype(np.int32))
    me.polygons.foreach_set("loop_start", (np.arange(len(F)) * 4).astype(np.int32)); me.polygons.foreach_set("loop_total", np.full(len(F), 4, np.int32))
    me.update(calc_edges=True)
    col = np.concatenate([np.array(colours, float).reshape(-1, 3), np.ones((len(V), 1))], 1)
    ca = me.color_attributes.new("col", "FLOAT_COLOR", "POINT"); ca.data.foreach_set("color", col.ravel())
    me.materials.append(material)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o); return o

def cloud_layer(name, centre, radius, thickness, cover=0.5, density=0.02, scale=900.0, stretch=(0.55, 1.0, 1.6), emit=0.02, emit_colour=(0.75, 0.8, 1.0), seed=0.0, detail=7.0, soft=0.14):
    """One flat disc of volume whose density comes from thresholded noise: ragged continuous cloud field
    with gaps, no lump outlines. `cover` lower = more cloud. Density fades to the slab's top and bottom."""
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=96, radius1=radius, radius2=radius, depth=thickness)
    m = bpy.data.materials.new(name); nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); nt.links.new(tc.outputs["Object"], mp.inputs[0])
    mp.inputs["Scale"].default_value = tuple(s / scale for s in stretch); mp.inputs["Location"].default_value = (seed * 3.7, seed * 1.3, seed)
    big = nt.nodes.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 1.0; big.inputs["Detail"].default_value = detail; big.inputs["Roughness"].default_value = 0.68; big.inputs["Distortion"].default_value = 0.15
    nt.links.new(mp.outputs[0], big.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    zz = nt.nodes.new("ShaderNodeMath"); zz.operation = "MULTIPLY"; zz.inputs[1].default_value = 2.0 / thickness; nt.links.new(sep.outputs["Z"], zz.inputs[0])
    z2 = nt.nodes.new("ShaderNodeMath"); z2.operation = "POWER"; z2.inputs[1].default_value = 2.0
    ab = nt.nodes.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; nt.links.new(zz.outputs[0], ab.inputs[0]); nt.links.new(ab.outputs[0], z2.inputs[0])
    sub = nt.nodes.new("ShaderNodeMath"); sub.operation = "MULTIPLY_ADD"; sub.inputs[1].default_value = -0.22; nt.links.new(z2.outputs[0], sub.inputs[0]); nt.links.new(big.outputs[0], sub.inputs[2])
    dens = _ramp(nt, sub.outputs[0], [(cover - 0.02, (0, 0, 0)), (cover + soft, (1, 1, 1))])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = density; nt.links.new(dens, mul.inputs[0])
    sc = nt.nodes.new("ShaderNodeVolumeScatter"); sc.inputs["Color"].default_value = (0.38, 0.43, 0.66, 1); sc.inputs["Anisotropy"].default_value = 0.3; nt.links.new(mul.outputs[0], sc.inputs["Density"])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*emit_colour, 1)
    es = nt.nodes.new("ShaderNodeMath"); es.operation = "MULTIPLY"; es.inputs[1].default_value = emit; nt.links.new(mul.outputs[0], es.inputs[0]); nt.links.new(es.outputs[0], em.inputs["Strength"])
    add = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(sc.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Volume"])
    return _obj(name, bm, m, centre, smooth=False)

def no_specular():
    """Lesson from earlier scenes: default specular turns dark surfaces grey. Call before render."""
    for m in bpy.data.materials:
        if m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED": n.inputs["Specular IOR Level"].default_value = 0.0

def project(p):
    """Reference-pixel coordinates (px, py) and depth of world points p (N,3) - the inverse of P(). numpy."""
    M = np.array(CAM.matrix_world.inverted()); q = np.asarray(p, float) @ M[:3, :3].T + M[:3, 3]
    f = CAM.data.lens / 18.0 * REF_W / 2; depth = -q[:, 2]
    return REF_W / 2 + q[:, 0] / depth * f, REF_H / 2 - q[:, 1] / depth * f, depth

def haze(strength, colour, size, at, scatter=0.0):
    """A bounded box of glowing haze: emission adds strength*colour per metre of view ray inside it (sunlit distance haze
    whose brightness is set directly, not by scattering)."""
    m = bpy.data.materials.new("haze"); nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*colour, 1); em.inputs["Strength"].default_value = strength
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"); last = em.outputs[0]
    if scatter:
        v = nt.nodes.new("ShaderNodeVolumeScatter"); v.inputs["Color"].default_value = (*colour, 1); v.inputs["Density"].default_value = scatter
        add = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(em.outputs[0], add.inputs[0]); nt.links.new(v.outputs[0], add.inputs[1]); last = add.outputs[0]
    nt.links.new(last, out.inputs["Volume"])
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(at) @ Matrix.Diagonal((*size, 1)))
    return _obj("haze", bm, m, smooth=False)
