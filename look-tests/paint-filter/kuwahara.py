"""Run an existing image through Blender's compositor Kuwahara node, headless.

Usage (from a kiln checkout):
    tools/bl <this file> <input.png> <out dir> <variants.json> [CPU|GPU]

variants.json is a list of objects. Each makes one output image <out dir>/<name>.png:
    name          file stem
    type          "Anisotropic" or "Classic"            (default Anisotropic)
    size          filter radius in pixels               (default 6)
    uniformity    anisotropic only: structure-tensor smoothing radius (default 4)
    sharpness     anisotropic only, 0..1                (default 1)
    eccentricity  anisotropic only, 0..1 in the UI, higher stretches more (default 1)
    high_precision classic only                         (default false)
    preblur       gaussian blur in pixels before the filter (default 0)
    posterize     posterise steps before the filter     (default 0 = off)
    canvas        0..1 strength of a noise "canvas" multiplied in afterwards
    edges         0..1 strength of edge darkening (Sobel of the filtered image)
    passes        run the Kuwahara node this many times in a row (default 1)
Prints one "TIME name seconds" line per variant.
"""
import json
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
src, outdir, spec = argv[0], argv[1], argv[2]
device = argv[3] if len(argv) > 3 else "CPU"

scene = bpy.context.scene
img = bpy.data.images.load(src)
w, h = img.size
r = scene.render
r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
r.use_compositing = True
r.compositor_device = device
# Standard view transform so an sRGB picture goes in and comes out unchanged.
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
if scene.camera is None:  # the render call wants a camera even though nothing is rendered
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam


def build(v):
    tree = bpy.data.node_groups.new(v["name"], "CompositorNodeTree")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = tree.nodes, tree.links
    out = N.new("NodeGroupOutput")
    im = N.new("CompositorNodeImage")
    im.image = img
    cur = im.outputs["Image"]

    if v.get("preblur", 0) > 0:
        b = N.new("CompositorNodeBlur")
        b.inputs["Size"].default_value = (v["preblur"], v["preblur"])
        L.new(cur, b.inputs["Image"])
        cur = b.outputs["Image"]
    if v.get("posterize", 0) > 0:
        # The compositor works on linear values, where equal steps crush the darks to
        # black; posterise in a display-like gamma and convert back.
        g1 = N.new("ShaderNodeGamma"); g1.inputs["Gamma"].default_value = 1 / 2.2
        p = N.new("CompositorNodePosterize")
        p.inputs["Steps"].default_value = v["posterize"]
        g2 = N.new("ShaderNodeGamma"); g2.inputs["Gamma"].default_value = 2.2
        L.new(cur, g1.inputs[0]); L.new(g1.outputs[0], p.inputs["Image"])
        L.new(p.outputs["Image"], g2.inputs[0])
        cur = g2.outputs[0]

    for _ in range(v.get("passes", 1)):
        k = N.new("CompositorNodeKuwahara")
        k.inputs["Type"].default_value = v.get("type", "Anisotropic")
        k.inputs["Size"].default_value = v.get("size", 6)
        k.inputs["Uniformity"].default_value = v.get("uniformity", 4)
        k.inputs["Sharpness"].default_value = v.get("sharpness", 1.0)
        k.inputs["Eccentricity"].default_value = v.get("eccentricity", 1.0)
        k.inputs["High Precision"].default_value = v.get("high_precision", False)
        L.new(cur, k.inputs["Image"])
        cur = k.outputs["Image"]

    def multiply(colour, factor_colour, strength):
        m = N.new("ShaderNodeMix")
        m.data_type = "RGBA"
        m.blend_type = "MULTIPLY"
        m.inputs[0].default_value = strength
        L.new(colour, m.inputs[6])
        L.new(factor_colour, m.inputs[7])
        return m.outputs[2]

    if v.get("edges", 0) > 0:
        f = N.new("CompositorNodeFilter")
        f.inputs["Type"].default_value = "Sobel"
        L.new(cur, f.inputs["Image"])
        inv = N.new("CompositorNodeInvert")
        L.new(f.outputs["Image"], inv.inputs["Color"])
        bw = N.new("CompositorNodeRGBToBW")
        L.new(inv.outputs[0], bw.inputs[0])
        cur = multiply(cur, bw.outputs[0], v["edges"])
    if v.get("canvas", 0) > 0:
        co = N.new("CompositorNodeImageCoordinates")
        L.new(im.outputs["Image"], co.inputs[0])
        # weave: two wave textures at right angles, plus fine noise, centred near 1
        sc = N.new("ShaderNodeVectorMath")
        sc.operation = "MULTIPLY"
        L.new(co.outputs["Pixel"], sc.inputs[0])
        sc.inputs[1].default_value = (1.2, 1.2, 1.2)
        wx = N.new("ShaderNodeTexWave"); wx.bands_direction = "X"
        wy = N.new("ShaderNodeTexWave"); wy.bands_direction = "Y"
        for wv in (wx, wy):
            wv.inputs["Scale"].default_value = 1.0
            wv.inputs["Distortion"].default_value = 1.5
            wv.inputs["Detail"].default_value = 1.0
            L.new(sc.outputs[0], wv.inputs["Vector"])
        add = N.new("ShaderNodeMath"); add.operation = "ADD"
        L.new(wx.outputs["Factor"], add.inputs[0]); L.new(wy.outputs["Factor"], add.inputs[1])
        rng = N.new("ShaderNodeMapRange")
        rng.inputs["From Min"].default_value = 0.0
        rng.inputs["From Max"].default_value = 2.0
        rng.inputs["To Min"].default_value = 0.8
        rng.inputs["To Max"].default_value = 1.15
        L.new(add.outputs[0], rng.inputs[0])
        cur = multiply(cur, rng.outputs[0], v["canvas"])

    L.new(cur, out.inputs[0])
    return tree


for v in json.load(open(spec)):
    scene.compositing_node_group = build(v)
    r.filepath = f"{outdir}/{v['name']}.png"
    t = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    print(f"TIME {v['name']} {time.perf_counter() - t:.3f}", flush=True)
