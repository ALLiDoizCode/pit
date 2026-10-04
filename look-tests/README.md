# Look tests

Throwaway prototypes that ask one question: can script-generated 3D carry the beauty, atmosphere and scale this game needs? They feed issue #1. Nothing here is game code, and none of it is held to a standard.

Renders and comparison sheets are written to `out/` folders, which are git-ignored: they include or trace copyrighted reference paintings.

## Running one

The scripts run in headless Blender through kiln's wrapper, from a checkout of [kiln](https://github.com/ALLiDoizCode/kiln):

```
tools/bl <path to pit>/look-tests/recreations/scene3/scene.py out.png 720 40
```

The arguments are the output file, width in pixels and samples. Each scene folder has its own copy of `kit.py`; the copies diverged as each scene added what it needed. The reference images are expected in kiln's git-ignored `docs/style/refs/owner/`.

## `style-variants/` (2026-10-04)

- `variants.py`: one crate and one rock in three styles (faceted, bevelled, detailed). The owner preferred the bevelled and detailed ones.
- `textures.py`: the detailed crate under four surface treatments. The owner chose "painted": a gradient from dark at the base to light at the top, light along exposed edges, shadow in crevices.
- `bake_proof.py`: bakes that painted look into a texture and into vertex colours and exports both. In Bevy the texture version matched the Blender reference; the vertex-colour version came out washed pale.
- `ledge_scene.py`: a first attempt at a whole scene. Weak, and kept as a record of why: the vegetation was solid lumps.

## `recreations/` (2026-10-04)

Nine reference scenes supplied by the owner (eight *Made in Abyss* backgrounds and one game screenshot), recreated without their characters. Each mass is placed by tracing where it sits in the reference image (`kit.P(px, py, distance)`).

| Scene | Subject | Rating out of 5 |
| --- | --- | --- |
| 1 | Cliff ledge above clouds | 2.5 |
| 2 | Town on the rim, looking across the pit | 2.5 |
| 3 | Inverted forest | 3 |
| 4 | Rock pillar between cliffs | 2.5 |
| 5 | Misty layered ledges | 2.5 |
| 6 | Looking down into the pit | 3 |
| 7 | Green forest with a giant arch | 2.5 |
| 8 | Basin with a dark hole | 2.5 |
| 9 | Game screenshot: forest clearing | 2.5 |

Ratings are each scene's builder judging its own result beside the reference, where 1 means only the layout is recognisable and 5 means it could pass as the same scene in another medium.

### What worked every time

- Composition and scale, from tracing.
- Palette, light-and-shadow scheme and distance haze. Checking region colours by number caught casts the eye missed.
- Scattering very large numbers of small things: buildings, grass blades, leaf cards.

### What failed every time

- The character of large forms: rock as smeared noise, trunks as smooth tubes, foliage as balls or flat confetti.
- Surfaces close to the camera, which look like untextured primitives.
- Clouds, which show the lumps they are built from and cast weak shadows.
- Brushwork: placed highlights, deliberately lost or sharp edges, designed silhouettes.

### Techniques worth keeping

For the engine (this repo):
- Distance haze that fades toward a painted backdrop colour chosen by view direction, independent of lighting (`backdrop_haze` in scene 3). Scattering fog kept washing the frame one pale colour.
- Shadow shapes traced from the reference and placed between the sun and the scene (`shadow_card` in scene 2, `shadow_disc` in scene 7).
- One noise-thresholded volume slab for a cloud layer (`cloud_layer` in scene 6).
- Translucency on leaf and grass cards, or back-lit foliage goes black (`two_sided` in scene 7).
- No specular on rock and foliage: the default sheen turned dark surfaces pale grey.

For assets (kiln):
- Foliage as leaf cards on a branch skeleton, with painted stroke textures, in place of solid shapes.
- Rock built from deliberate planes, ledges and fractures in place of noise.
- Painted colour variation on every surface.
