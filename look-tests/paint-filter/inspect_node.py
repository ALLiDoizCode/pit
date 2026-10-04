"""Print what the compositor Kuwahara node really exposes in this Blender."""
import bpy
print("VERSION", bpy.app.version_string)
scene = bpy.context.scene
tree = bpy.data.node_groups.new("probe", "CompositorNodeTree")
print("scene compositing attrs:", [a for a in dir(scene) if "compos" in a.lower() or a in ("node_tree", "use_nodes")])
n = tree.nodes.new("CompositorNodeKuwahara")
print("PROPS")
for p in n.bl_rna.properties:
    if p.identifier in bpy.types.Node.bl_rna.properties.keys():
        continue
    extra = ""
    if p.type == "ENUM":
        extra = [e.identifier for e in p.enum_items]
    print("  ", p.identifier, p.type, extra)
print("INPUTS")
for s in n.inputs:
    d = getattr(s, "default_value", None)
    try: d = tuple(d)
    except TypeError: pass
    rna = s.bl_rna.properties.get("default_value")
    rng = (getattr(rna, "soft_min", None), getattr(rna, "soft_max", None)) if rna else None
    items = None
    if s.type == "MENU":
        try: items = [e.identifier for e in s.bl_rna.properties["default_value"].enum_items]
        except Exception as e: items = repr(e)
    print("  ", repr(s.name), s.identifier, s.type, d, rng, items, "enabled" if s.enabled else "disabled")
print("OUTPUTS", [(s.name, s.type) for s in n.outputs])
for t in ("CompositorNodeImage", "CompositorNodeViewer", "CompositorNodeComposite", "NodeGroupOutput", "CompositorNodeOutputFile", "CompositorNodePosterize", "CompositorNodeBlur", "CompositorNodeFilter", "ShaderNodeMix", "CompositorNodeMixRGB", "ShaderNodeTexNoise", "CompositorNodeTexture", "ShaderNodeMath"):
    try:
        m = tree.nodes.new(t)
        print("OK ", t, [(s.name, s.type) for s in m.inputs], "->", [s.name for s in m.outputs], [p.identifier for p in m.bl_rna.properties if p.identifier not in bpy.types.Node.bl_rna.properties.keys()])
    except Exception as e:
        print("NO ", t, e)
