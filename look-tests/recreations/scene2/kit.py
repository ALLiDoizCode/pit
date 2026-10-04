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

def rock_material(name, rock=("#2e2a2b", "#5b5352", "#8a7d76"), grass=("#3f8f2a", "#7fd036"), streak=1.0, grass_from=0.62, patch=None, moss=None, patch_scale=0.02, grass_scale=0.25):
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
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = grass_scale; n2.inputs["Detail"].default_value = 6; nt.links.new(geo.outputs["Position"], n2.inputs["Vector"])
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

def cliff(name, lip, base, material, back=20.0, rise=0.0, rough=1.0, cols=170, rows=64, seed=0, jag=0.0):
    """A rock mass traced from the reference: `lip` is its top edge and `base` where its face
    ends, both as (px, py, distance). The face is lofted between them; the top runs back from the lip."""
    lip_w = [P(*p) for p in _resample(lip, cols)]; base_w = [P(*p) for p in _resample(base, cols)]
    bm = bmesh.new(); off = Vector((seed * 3.1, seed * 1.7, seed)); grid = []
    if jag:     # ragged skyline: notch the lip up and down along its length
        for c in range(cols):
            dd = (lip_w[c] - CAM.location).length
            lip_w[c].z += jag * dd * 0.02 * (_ridged(Vector((c * 0.035, seed * 7.3, 0))) * 0.8 + noise.noise(Vector((c * 0.11, seed * 3.1, 5))) * 0.45)
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
def cloud(name, centre, radius, density=1.0, seed=0, squash=0.5, stretch=1.5, wisp=0.55):
    """A cloud: a lumpy shell filled with scattering, thinned by noise so its edges go wispy."""
    o = puff(name, centre, radius, flat_material("tmp", "#ffffff"), n=22, squash=squash, seed=seed, lump=(0.45, 0.75), stretch=(stretch, stretch, 1), subdiv=2, bumpy=0.25)
    m = bpy.data.materials.new(name); nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc = nt.nodes.new("ShaderNodeTexCoord"); no = nt.nodes.new("ShaderNodeTexNoise")
    no.inputs["Scale"].default_value = 2.2 / radius; no.inputs["Detail"].default_value = 7; no.inputs["Roughness"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], no.inputs["Vector"])
    dens = _ramp(nt, no.outputs[0], [(wisp - 0.12, (0, 0, 0)), (wisp + 0.16, (1, 1, 1))])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = density * 2.6 / radius; nt.links.new(dens, mul.inputs[0])
    sc = nt.nodes.new("ShaderNodeVolumeScatter"); sc.inputs["Color"].default_value = (1, 1, 1, 1); sc.inputs["Anisotropy"].default_value = 0.5
    nt.links.new(mul.outputs[0], sc.inputs["Density"])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.8, 0.9, 1.0, 1)      # stands in for light bounced around inside
    es = nt.nodes.new("ShaderNodeMath"); es.operation = "MULTIPLY"; es.inputs[1].default_value = 0.11; nt.links.new(mul.outputs[0], es.inputs[0]); nt.links.new(es.outputs[0], em.inputs["Strength"])
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


# ---- added for scene 5 -------------------------------------------------------------------
def H(px, py, h):
    """(px, py, d) where the ray through reference pixel (px, py) meets the level plane h metres below the camera.
    Use for lips of flat shelves seen from above, so the whole lip is coplanar."""
    v = (P(px, py, 1.0) - CAM.location)
    return (px, py, -h / min(v.z, -1e-4))

def emit_material(name, colour, vary=0.0, scale=1.0):
    """Unlit flat colour (for silhouettes whose painted colour must come out exactly), with optional noise variation."""
    m = bpy.data.materials.new(name); nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    em = nt.nodes.new("ShaderNodeEmission"); c = srgb(colour)
    if vary:
        geo = nt.nodes.new("ShaderNodeNewGeometry"); no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = scale; no.inputs["Detail"].default_value = 4
        nt.links.new(geo.outputs["Position"], no.inputs["Vector"])
        nt.links.new(_ramp(nt, no.outputs[0], [(0.3, tuple(x * (1 - vary) for x in c)), (0.7, tuple(x * (1 + vary) for x in c))]), em.inputs["Color"])
    else: em.inputs["Color"].default_value = (*c, 1)
    nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    return m

def sky(horizon, low, high, band, strength=1.0, band_amount=0.7, stretch=(3, 3, 40), elev=(0.0, 0.08, 0.22), seed=0.0, big=None, side=0.0):
    """Painted overcast sky as the world background: a vertical gradient with horizontal streaks of grey cloud."""
    w = scene.world; nt = w.node_tree; bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    grad = _ramp(nt, sep.outputs["Z"], [(elev[0], horizon), (elev[1], low), (elev[2], high)])
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = stretch; mp.inputs["Location"].default_value = (seed, seed * 0.7, seed * 1.3); nt.links.new(tc.outputs["Generated"], mp.inputs[0])
    no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 1.0; no.inputs["Detail"].default_value = 6; no.inputs["Roughness"].default_value = 0.6; nt.links.new(mp.outputs[0], no.inputs["Vector"])
    f = _ramp(nt, no.outputs[0], [(0.45, (0, 0, 0)), (0.7, (band_amount,) * 3)])
    rgb = nt.nodes.new("ShaderNodeRGB"); rgb.outputs[0].default_value = (*srgb(band), 1)
    col = _mix(nt, "MIX", f, grad, rgb.outputs[0])
    if big:     # broad flat cloud masses: (colour, amount, threshold)
        mp2 = nt.nodes.new("ShaderNodeMapping"); mp2.inputs["Scale"].default_value = (stretch[0] * 0.45, stretch[1] * 0.45, stretch[2] * 0.3); mp2.inputs["Location"].default_value = (seed + 4.2, 1.7, seed * 0.3 + 2.0); nt.links.new(tc.outputs["Generated"], mp2.inputs[0])
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 1.0; n2.inputs["Detail"].default_value = 5; n2.inputs["Roughness"].default_value = 0.55; nt.links.new(mp2.outputs[0], n2.inputs["Vector"])
        f2 = _ramp(nt, n2.outputs[0], [(big[2], (0, 0, 0)), (big[2] + 0.07, (big[1],) * 3)])
        f2 = _mix(nt, "MULTIPLY", 1.0, f2, _ramp(nt, sep.outputs["Z"], [(elev[1] * 0.6, (1, 1, 1)), (elev[2], (0.15, 0.15, 0.15))]))   # mostly low in the sky
        r2 = nt.nodes.new("ShaderNodeRGB"); r2.outputs[0].default_value = (*srgb(big[0]), 1)
        col = _mix(nt, "MIX", f2, col, r2.outputs[0])
    if side:    # darker toward the left and right of the view (camera looks along +Y)
        ab = nt.nodes.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; nt.links.new(sep.outputs["X"], ab.inputs[0])
        col = _mix(nt, "MULTIPLY", 1.0, col, _ramp(nt, ab.outputs[0], [(0.12, (1, 1, 1)), (0.5, (side,) * 3)]))
    nt.links.new(col, bg.inputs["Color"]); bg.inputs["Strength"].default_value = strength


# ---- added for scene 2 (town on a pit rim) -------------------------------------------------
def hit(px, py, far=1e5):
    """World point and normal where the view ray through reference pixel (px, py) meets the geometry built so far."""
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    d = (P(px, py, 1.0) - CAM.location).normalized()
    ok, loc, nrm, _, _, _ = scene.ray_cast(dg, CAM.location, d, distance=far)
    return (loc.copy(), nrm.copy()) if ok else (None, None)

def varied_material(name, colours, emit=0.0, rough=1.0):
    """One flat colour per mesh island, picked at random from the list (walls, roofs, petals, leaves)."""
    m = bpy.data.materials.new(name); nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = rough
    geo = nt.nodes.new("ShaderNodeNewGeometry"); n = nt.nodes.new("ShaderNodeValToRGB"); n.color_ramp.interpolation = "CONSTANT"; e = n.color_ramp.elements
    while len(e) < len(colours): e.new(0.5)
    for i, (el, c) in enumerate(zip(e, colours)): el.position, el.color = i / len(colours), (*srgb(c), 1)
    nt.links.new(geo.outputs["Random Per Island"], n.inputs[0]); nt.links.new(n.outputs[0], bsdf.inputs["Base Color"])
    if emit: nt.links.new(n.outputs[0], bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = emit
    return m

def houses(name, items, wall_mat, roof_mat):
    """Many small gabled buildings in one mesh. items: (position Vector of the base centre, width, depth, wall height, roof height, yaw)."""
    bm = bmesh.new()
    for pos, w, dp, h, rh, yaw in items:
        M = Matrix.Translation(pos) @ Matrix.Rotation(yaw, 4, "Z")
        r = bmesh.ops.create_cube(bm, size=1.0, matrix=M @ Matrix.Translation((0, 0, h / 2 - 1.0)) @ Matrix.Diagonal((w, dp, h + 2.0, 1)))
        o = 0.12 * w; a, b = w / 2 + o, dp / 2 + o
        vs = [bm.verts.new(M @ Vector(c)) for c in [(-a, -b, h), (a, -b, h), (a, b, h), (-a, b, h), (0, -b, h + rh), (0, b, h + rh)]]
        for idx in [(0, 4, 5, 3), (4, 1, 2, 5), (0, 1, 4), (3, 5, 2), (0, 3, 2, 1)]:
            f = bm.faces.new([vs[i] for i in idx]); f.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _obj(name, bm, wall_mat, smooth=False); o.data.materials.append(roof_mat)
    return o

def card_px(name, pts, material, shift=None):
    """A flat polygon traced in reference pixels: pts are (px, py, d). `shift` moves it bodily (used for shadow casters)."""
    bm = bmesh.new(); vs = [bm.verts.new(P(*p) + (Vector(shift) if shift else Vector())) for p in pts]; bm.faces.new(vs)
    return _obj(name, bm, material, smooth=False)

def shadow_card(pts, sun_dir, t=200.0):
    """Paint a shadow: an unseen polygon moved t metres toward the sun from the traced shape (px, py, d), so its shadow lands there."""
    o = card_px("shadow_card", pts, flat_material("shadow_card", "#000000"), shift=-Vector(sun_dir).normalized() * t)
    o.visible_camera = False; o.visible_diffuse = False; o.visible_glossy = False
    return o

def slab(name, pts, h, thick, material):
    """A level stone slab: its top outline traced in reference pixels (px, py), lying h metres below the camera."""
    top = [P(*H(x, y, h)) for x, y in pts]; bm = bmesh.new()
    tv = [bm.verts.new(p) for p in top]; bv = [bm.verts.new(p - Vector((0, 0, thick))) for p in top]; n = len(tv)
    bm.faces.new(tv)
    for i in range(n): bm.faces.new((tv[i], tv[(i + 1) % n], bv[(i + 1) % n], bv[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, material, smooth=False)

def stone_material(name, a, b, mortar, scale=2.5, angle=0.0, brick=True):
    """Paving: bricks (or plain blotchy stone) with darker joints."""
    m = bpy.data.materials.new(name); nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 1.0
    geo = nt.nodes.new("ShaderNodeNewGeometry"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, angle); nt.links.new(geo.outputs["Position"], mp.inputs[0])
    no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 1.5; no.inputs["Detail"].default_value = 8; nt.links.new(geo.outputs["Position"], no.inputs["Vector"])
    col = _ramp(nt, no.outputs[0], [(0.3, a), (0.7, b)])
    if brick:
        br = nt.nodes.new("ShaderNodeTexBrick"); br.inputs["Scale"].default_value = scale; br.inputs["Mortar Size"].default_value = 0.03 if scale > 1 else 0.006
        br.inputs["Color1"].default_value = (1, 1, 1, 1); br.inputs["Color2"].default_value = (0.75, 0.75, 0.75, 1); br.inputs["Mortar"].default_value = (0.25, 0.25, 0.25, 1)
        nt.links.new(mp.outputs[0], br.inputs["Vector"]); col = _mix(nt, "MULTIPLY", 1.0, col, br.outputs["Color"])
    nt.links.new(col, bsdf.inputs["Base Color"])
    return m

def petals(name, items, material, seed=0):
    """Loose petals / leaf cards: items are (centre Vector, length, width); each is a pointed oval turned at random."""
    rnd = random.Random(seed); bm = bmesh.new()
    for c, ln, wd in items:
        n = (CAM.location - c).normalized(); n = (n + Vector((rnd.uniform(-.5, .5), rnd.uniform(-.5, .5), rnd.uniform(-.5, .5)))).normalized()
        t1 = n.orthogonal().normalized(); t1.rotate(Matrix.Rotation(rnd.uniform(0, math.tau), 3, n)); t2 = n.cross(t1)
        ring = [(1, 0), (0.55, 0.42), (0, 0.5), (-0.6, 0.38), (-1, 0), (-0.6, -0.38), (0, -0.5), (0.55, -0.42)]
        bm.faces.new([bm.verts.new(c + t1 * ln * a + t2 * wd * b) for a, b in ring])
    return _obj(name, bm, material, smooth=False)

def flower(name, centre, r, petal_mat, leaf_mat, seed=0, n=6, leaves=5):
    """A star flower facing the camera and a little upward, with a rosette of broad leaves under it."""
    rnd = random.Random(seed); bm = bmesh.new(); lb = bmesh.new()
    ax = ((CAM.location - centre).normalized() + Vector((rnd.uniform(-.3, .3), rnd.uniform(-.2, .2), 0.5))).normalized()
    t1 = ax.orthogonal().normalized(); t2 = ax.cross(t1); a0 = rnd.uniform(0, math.tau)
    for i in range(n):
        a = a0 + i * math.tau / n; d = t1 * math.cos(a) + t2 * math.sin(a); s = ax.cross(d); L = r * rnd.uniform(0.85, 1.1)
        pts = [centre, centre + d * L * 0.5 + s * L * 0.3 + ax * L * 0.1, centre + d * L + ax * L * 0.25, centre + d * L * 0.5 - s * L * 0.3 + ax * L * 0.1]
        bm.faces.new([bm.verts.new(p) for p in pts])
    for i in range(leaves):
        a = rnd.uniform(0, math.tau); d = (t1 * math.cos(a) + t2 * math.sin(a)); s = ax.cross(d); L = r * rnd.uniform(1.0, 1.6); c = centre - ax * r * rnd.uniform(0.9, 1.6) + d * r * 0.5
        pts = [c, c + d * L * 0.5 + s * L * 0.36, c + d * L - ax * L * 0.15, c + d * L * 0.5 - s * L * 0.36]
        lb.faces.new([lb.verts.new(p) for p in pts])
    _obj(name + "_leaves", lb, leaf_mat, smooth=False)
    return _obj(name, bm, petal_mat, smooth=False)

def sea(h, near, mid, far, glare=None, radius=90000.0, start=1200.0):
    """A sea: a huge level disc h metres below the camera, unlit, graded from near to far colour, with a paler glare band to one side."""
    m = bpy.data.materials.new("sea"); nt = m.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs[0])
    col = _ramp(nt, sep.outputs["Y"], [(0.0, near), (6000.0 / radius, mid), (40000.0 / radius, far)])
    # the ramp wants 0..1: scale Y first
    sc = nt.nodes.new("ShaderNodeMath"); sc.operation = "DIVIDE"; sc.inputs[1].default_value = radius; nt.links.new(sep.outputs["Y"], sc.inputs[0])
    col.node.inputs[0].links and nt.links.remove(col.node.inputs[0].links[0]); nt.links.new(sc.outputs[0], col.node.inputs[0])
    if glare:   # (colour, x_from_ratio, x_to_ratio): paler where x/y is below the ratio (the left of the view)
        dv = nt.nodes.new("ShaderNodeMath"); dv.operation = "DIVIDE"; nt.links.new(sep.outputs["X"], dv.inputs[0]); nt.links.new(sep.outputs["Y"], dv.inputs[1])
        g = _ramp(nt, dv.outputs[0], [(0.0, (1, 1, 1)), (1.0, (0, 0, 0))])
        g.node.color_ramp.elements[0].position = 0.0; g.node.color_ramp.elements[1].position = 1.0
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = glare[1]; mr.inputs[2].default_value = glare[2]; nt.links.new(dv.outputs[0], mr.inputs[0]); nt.links.remove(g.node.inputs[0].links[0]); nt.links.new(mr.outputs[0], g.node.inputs[0])
        rgb = nt.nodes.new("ShaderNodeRGB"); rgb.outputs[0].default_value = (*srgb(glare[0]), 1)
        no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 0.0004; no.inputs["Detail"].default_value = 6; nt.links.new(geo.outputs["Position"], no.inputs["Vector"])
        g = _mix(nt, "MULTIPLY", 1.0, g, _ramp(nt, no.outputs[0], [(0.3, (0.4, 0.4, 0.4)), (0.7, (1, 1, 1))]))
        col = _mix(nt, "MIX", g, col, rgb.outputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(col, em.inputs["Color"])
    nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    bm = bmesh.new(); z = CAM.location.z - h; bm.faces.new([bm.verts.new(p) for p in [(-radius, start, z), (radius, start, z), (radius, radius, z), (-radius, radius, z)]])
    CAM.data.clip_end = radius * 2
    return _obj("sea", bm, m, smooth=False)
