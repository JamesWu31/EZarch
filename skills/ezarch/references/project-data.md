# Optional project.yml API

This is the input contract for the optional `model`, `views`, `brief` and `diagram` helpers, not a universal project schema. Use it only when invoking those helpers. Existing files, direct ezdxf/bpy/CadQuery calls, SVG, CSV, image coordinates and other project structures do not need to adopt it.

Within this API, lengths/positions are millimetres and colors are RGB components from 0 to 1. IDs are filename-safe; stable IDs help when using its cross-file comparisons. The example illustrates fields, not a required building type, design method or deliverable set.

```yaml
schema_version: 1
name: Small house
subtitle: A measured architectural study
units: mm
north_angle: 0
materials:
  plaster: {color: [0.78, 0.77, 0.72], roughness: 0.75, texture: plaster}
  metal: {color: [0.15, 0.16, 0.14], roughness: 0.3, metallic: 0.7}
  glass: {color: [0.85, 0.93, 0.91], roughness: 0.05, transmission: 1, texture: glass}
elements:
  - id: south-wall
    kind: wall
    start: [0, 0]
    end: [6000, 0]
    thickness: 250
    height: 3000
    material: plaster
    openings:
      - {offset: 2000, width: 1800, sill: 900, height: 1600,
         type: window, frame_material: metal, glass_material: glass, panels: 2}
rooms:
  - id: living
    name: Living
    type: interior
    polygon: [[125,125], [5875,125], [5875,4000], [125,4000]]
views:
  - {id: plan, kind: plan, cut_z: 1200, scale: 100, title: Ground plan}
  - {id: section-a, kind: section, axis: y, at: 2000, scale: 100, title: Section A}
cameras:
  - {id: perspective, position: [10000,-10000,5000], target: [3000,2000,1200], lens: 40, aspect: 1.5}
```

## Elements

| kind | Required geometric fields | Optional fields |
|---|---|---|
| box / slab | origin [x,y,z], size [dx,dy,dz] | rotation, fillet_mm |
| wall | start/end [x,y], thickness, height | z, openings |
| cylinder | origin [x,y,z], radius, height | category |
| extrusion | polygon [[x,y],...], height | z, rotation |
| stair | origin, steps, rise, run, width | rotation |
| step | file (relative STEP path) | origin, rotation |
| dxf_extrusion | file, layer, height | origin, rotation |

All helper elements require `id`, `material`; `category` controls drawing inclusion and render treatment. Useful categories include wall, slab, roof, frame, glass, door, furniture, finish, water, site. Openings support passage, window, glass_door or door, with offset/width/sill/height. Window panels, frame width/depth and materials are configurable. Door solids use a closed leaf; plans replace that leaf with an opening arc and open leaf. `swing_side: 1` opens to the left of the wall direction; `-1` reverses it.

Any element may specify `cuts`, a list of box or cylinder cutters for actual geometric openings. Cutters use the coordinates of the element shape after its primary placement, before optional final rotation. A surface color or diagrammatic patch does not alter the solid geometry.

This schema requires valid positive-area room polygons; `brief` additionally rejects same-level overlap for its net-area calculation. Overlapping analytical regions can use their own data/calculation instead. `type: courtyard` excludes that area from interior net area. Optional fields: plan_name (short plan label), label_at, label:false, fill, diagram_color, grid_mm.

Dimensions: `id`, `p1`, `p2`, `base`, `view` (kind or exact view ID). Built-in dimension annotations are horizontal/vertical; oblique/radial dimensions require an explicit ezdxf/vector adapter. Sections/elevations may set `levels: [0, 3400, 4620]` in mm. Annotations: `view`, `points` and/or `text`, `at`, `size`. Exact geometry also supports project-local scripts for custom forms, rather than growing a one-case-specific schema.

## Views, cameras and rendering

Views have ID/kind/title/scale; optional paper_mm, margin and exclude categories. `decoration: true` opts into the example footer; default views contain no footer. `font` selects a font file relative to the project YAML (or an absolute path); rich drafting views accept a `style` parameter dictionary. Plans set cut_z. Sections set axis x/y and at. Elevations/axons set normal/xdir. Curves are sampled with controlled geometric tolerance for polyline presentation; original exact shapes remain in STEP.

Cameras: position/target in mm, lens in mm, aspect, optional orthographic:true and ortho_scale in mm. `render` config supports sun_elevation/sun_rotation in degrees, sun_energy, sky_strength and exposure. Lighting is a visual study unless a location/time-based simulation is explicitly provided.

Landscape: `kind: tree`, position [x,y,z], height, crown_radius and stable seed. Trees are render decoration and symbolic plan canopies, not exact botanical CAD solids.

`brief` contains requirements/assumptions and optional `routes: [[[x,y],...],...]` for circulation diagrams. `sources` stores reference URLs, dimensions and confidence notes. None of these inputs should contain private absolute paths when intended for redistribution.

## External models and custom geometry

For a CAD model supplied as STEP, use a `kind: step` element with `file`, `material` and optional `origin`; the STEP file is resolved relative to the project YAML and hashed as a dependency. For 2D-to-3D use `kind: dxf_extrusion`, `file`, `layer`, `height`: it converts documented DXF units to mm and extrudes closed, straight XY LWPOLYLINE boundaries. Unitless, curved, overlapping, nested or nonplanar boundaries fail explicitly so the AI can resolve their semantics in a project script. Original files are never modified. For external meshes use Blender's supported importers or trimesh and explicitly resolve units. Existing DXF layers, entities and blocks can be inspected or edited with ezdxf. Extrusion heights may come from supplied dimensions or explicit design assumptions, as the task permits.

These helpers do not import arbitrary native SKP/DWG or curved-BRep 3DM. Generated exchange formats and target-app import are described in [exchange-verification.md](exchange-verification.md); they do not imply universal native object support. Native control remains deferred.


## Optional semantic and expression fields

Optional top-level `levels: [{id: L0, elevation_mm: 0}, ...]`, `site`, `assemblies`, `requirements` retain project-specific semantics without imposing a building type. When levels exist, every room and plan view names a known `level`; plan `floor_z` clips projected geometry below that storey and `cut_z` defines the cutting height. A floor is not selected merely by moving the cut plane. Room overlap checks compare only the same level. Element metadata may include level, assembly, type_code, provenance.

A view with `drafting: []` uses the richer Drawing adapter. Add commands such as `{op: axis, name: '1', orientation: x, at: 0, start: -3000, end: 12000}`, `{op: level, point: [-1000, 0], value_mm: 0}`, `{op: furniture, kind: table, origin: [2000,2000], size: [1800,900]}`. `drawing_bounds` explicitly includes annotations; `exclude_ids` supports per-view omission. Commands are allow-listed, not arbitrary code. Custom forms and oblique dimensions remain accessible through project scripts and the full API.

PBR `materials.<name>.maps` accepts base_color/roughness/normal/metallic file paths relative to the project. texture_size_m is the physical repeat size. Generated meshes receive planar UVs in world metres; normal textures use tangent space. Imported public models preserve their authored UVs/materials.

`render.hdri` is a downloaded project image path; hdri_rotation is degrees. `render.lights` accepts AREA-light id, position/target in mm, size_mm [width,height], power_w and color. `render.asset_instances` accepts id, downloaded GLB/GLTF/BLEND file, source_url, position in mm, rotation_z in degrees and uniform scale. Origin is the asset footprint centre and bottom; default asset units are metres. Imported model sizes are saved in render-report.json. This importer packs supported image dependencies into BLEND. Its project fingerprint includes asset/PBR/HDRI files and local GLTF buffers/images, using portable relative dependency keys. It rejects remote GLTF URIs and expects downloaded dependencies; direct Blender workflows may manage assets differently.

When source-version checks are useful, independent styles or scripts can be associated with a report using `source_bindings: [{file: relative/path/from/report/to/style.yml, sha256: digest}]`; `audit` checks current content. This metadata is optional, not a prerequisite for edits or delivery. If a report is used as evidence that output matches particular sources, its hashes need to identify the sources actually used.
