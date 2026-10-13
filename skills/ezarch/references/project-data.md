# Project data and extension points

`project.yml` uses a validated top-level contract. Lengths/positions are millimetres, colors are RGB components from 0 to 1. Keep IDs stable and filename-safe. The agent writes this data from the user's brief and source observations.

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

All require `id`, `material`; `category` controls drawing inclusion and render treatment. Useful categories include wall, slab, roof, frame, glass, door, furniture, finish, water, site. Openings support passage, window, glass_door or door, with offset/width/sill/height. Window panels, frame width/depth and materials are configurable. Door solids use a closed leaf; plans replace that leaf with a measured opening arc and open leaf. `swing_side: 1` opens to the left of the wall direction; `-1` reverses it. Check the intended swing and avoid furniture collisions.

Any element may specify `cuts`, a list of box or cylinder cutters with the corresponding geometric fields. Use these for real slab openings, sunken pools and planting pits; do not hide an uncut floor with a colored patch and call it a geometric opening. Cutters use the coordinates of the element shape after its primary placement, before optional final rotation.

Room polygons must be valid and non-overlapping. `type: courtyard` excludes that area from interior net area. Optional fields: plan_name (short plan label), label_at, label:false, fill, diagram_color, grid_mm.

Dimensions: `id`, `p1`, `p2`, `base`, `view` (kind or exact view ID). Built-in dimension annotations are horizontal/vertical; oblique/radial dimensions require an explicit ezdxf/vector adapter. Sections/elevations may set `levels: [0, 3400, 4620]` in mm. Annotations: `view`, `points` and/or `text`, `at`, `size`. Exact geometry also supports project-local scripts for custom forms, rather than growing a one-case-specific schema.

## Views, cameras and rendering

Views have ID/kind/title/scale; optional paper_mm, margin and exclude categories. Plans set cut_z. Sections set axis x/y and at. Elevations/axons set normal/xdir. Curves are sampled with controlled geometric tolerance for polyline presentation; original exact shapes remain in STEP.

Cameras: position/target in mm, lens in mm, aspect, optional orthographic:true and ortho_scale in mm. `render` config supports sun_elevation/sun_rotation in degrees, sun_energy, sky_strength and exposure. Lighting is a visual study unless a location/time-based simulation is explicitly provided.

Landscape: `kind: tree`, position [x,y,z], height, crown_radius and stable seed. Trees are render decoration and symbolic plan canopies, not exact botanical CAD solids.

`brief` contains requirements/assumptions and optional `routes: [[[x,y],...],...]` for circulation diagrams. `sources` stores reference URLs, dimensions and confidence notes. None of these inputs should contain private absolute paths when intended for redistribution.

## External models and custom geometry

For a CAD model supplied as STEP, use a `kind: step` element with `file`, `material` and optional `origin`; the STEP file is resolved relative to the project YAML and hashed as a dependency. For 2D-to-3D use `kind: dxf_extrusion`, `file`, `layer`, `height`: it converts documented DXF units to mm and extrudes closed, straight XY LWPOLYLINE boundaries. Unitless, curved, overlapping, nested or nonplanar boundaries fail explicitly so the AI can resolve their semantics in a project script. Original files are never modified. For external meshes use Blender's supported importers or trimesh and explicitly resolve units. For existing DXF use ezdxf to inspect and preserve layers, entities and blocks; lift only geometry with known heights into 3D.

An arbitrary native SKP/DWG or curved-BRep 3DM cannot be assumed readable by the phase-one helpers. The first phase guarantees generated exchange files suitable for the named target software; it does not claim universal import of every native proprietary object. Do not silently discard unsupported objects. Native import/control remains a declared second-phase capability.
