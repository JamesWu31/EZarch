# Exact geometry and architectural drawings

Read [project-data.md](project-data.md). The `model` module builds valid OCCT solids and named components from the project, exports STEP and a mesh scene, and creates exchange formats. `views` performs actual plane intersections and OCCT hidden-line projection; it does not draw a separate lookalike model.

For freeform work beyond the standard components, save a project-local CadQuery script that constructs `Part(id, shape, material, category)` values, uses `mesh_scene`, and passes the same parts to `extract_view`. Keep exact shapes available for STEP export and validation. Choose lofts/sweeps/Boolean solids or Blender mesh modeling according to the geometry required; do not reduce a curved design to the box helper's limitations.

Plan: set the actual `cut_z`, visible depth and excluded categories. Elevation: supply the viewing `normal` and rightward `xdir`; up is their cross product. Section: set axis and location, check which half remains. The built-in x section looks towards negative x, y section towards positive y. For an arbitrary cut, use the same OCCT plane/clip pattern in a project script and record the plane explicitly.

Inspect cut poche, doors and windows, roof lines, stairs, furniture and annotations. A geometric projection still needs architectural semantics; add measured opening/door-swing annotations and explicit stair break rules when required. Do not "repair" an intentional break found in a reference.

Model space uses mm at 1:1. View `scale: 100` means 1:100. Fixed paper sizes fail if the model does not fit, rather than silently scaling. The PDF scale bar is independently measurable. DXF uses true DIMENSION entities calculated from the same endpoints. Dimensions and external annotation updates must be regenerated after edits; no blanket claim of associative CAD constraints.

Output: each view has DXF, SVG, vector PDF, PNG preview, geometry JSON and a report. Keep source IDs in geometry records, and inspect local details at a useful resolution. For supplied 2D CAD, inspect units/layers/blocks with ezdxf, use existing entities where possible, and keep any inferred extrusion heights explicit.

Sections suppress uncut background geometry below the 0 mm ground datum by default while preserving genuinely cut foundations and basins. For a basement / uneven terrain drawing, set `projection_min_z` to the appropriate elevation or `null` to retain all projected underground geometry; model and annotate the earth boundary explicitly. This is a drawing convention, not a change to the source solids.
