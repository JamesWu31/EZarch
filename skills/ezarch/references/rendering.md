# Rendering

Run `render <scene.json|blend|glb|gltf|obj|ply|stl> --out <dir>`. A render can start from an external model without running the design module. GLB has metre-based coordinates; OBJ/PLY/STL require `--source-units mm|m`, chosen from documented source dimensions. Do not guess units; the adapter applies the declared conversion. GLB/GLTF use their metre convention. Direct SKP/DWG and arbitrary NURBS 3DM import are deferred; do not tell the user these files were read if they were not.

For the exact model route, `model` creates `scene.json` with named geometry, mm coordinates and materials. The Blender worker converts it to metres, preserves component IDs, and records the imported bounds. Source STEP remains the exact geometry deliverable. The `.blend` scene is the editable rendering deliverable.

Use `--quality preview` first. Choose project cameras intentionally: position, target, lens, aspect and optional orthographic scale. For architectural exteriors, a convincing eye-level courtyard or façade composition is often more useful than only an overhead image. Inspect a second viewpoint to reveal concealed defects.

Materials use real-world object coordinates and physical parameters. Keep wall whites below a clipped white, add restrained micro-bump, use actual frame/glass thickness, and coordinate paving scale with the drawings. The procedural vegetation helper provides branches and individual leaves; replace or refine it when its silhouette or realism is inadequate for the camera. Preserve provenance for downloaded assets.

Blender is the final render environment. The worker detects supported GPU backends and records CPU fallback. Do not promise GPU use from hardware marketing names. Rendering uses Cycles, AgX and a fixed seed. A lower-noise final render is not a substitute for correcting bad materials, perspective or composition.

After reviewing a preview, refine the project/material/camera configuration, then use `--quality final --width <px> --samples <n>`. Required pixel width = intended printed width in mm / 25.4 × target PPI. Check noise, edges, glass and foliage at both whole-image and detail scale.

The renderer writes PNG, scene.blend, source-bounds evidence, selected backend and Blender log. Existing BLEND input preserves its scene lighting and camera where present. Changes to geometry require a rebuilt source scene; changing only lighting/camera need not redesign the building.
