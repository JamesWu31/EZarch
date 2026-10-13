# Exchange and verification

`model` saves exact STEP, scene.json and optional GLB/3DM/DAE. `exchange scene.json --formats glb 3dm dae` can run independently of building a model. GLB uses metres, 3DM uses millimetres, DAE declares `unitmeter=0.001` and `Z_UP`. Objects retain names; 3DM and DAE are editable mesh exchanges. Their parameter history and exact surface representation are not preserved; keep the companion STEP and project script.

Generated DXF contains editable CAD entities and native dimensions. Include the bundled font files as appropriate and a verified PDF for stable appearance. Target software import should be tested when that application is available; open-library re-read is evidence of format/geometry correctness, not a claim of having opened the commercial app.

Use `audit <project.yml> --out <report-dir>` with outputs under that project's `outputs` directory. It checks available model/views/renders, compares source hashes, reads saved formats and checks dimensions and PDF scale controls. A subset task is audited as a subset; absent unrequested modules are not fabricated successes.

For the visual pass open the actual files after the last edit. Record evidence in a project-local review: image inspected, concrete finding, correction and resulting image. Review a full page plus critical crops when necessary. Require a meaningful drawing/model alignment check rather than checking only that all filenames exist.

Useful tests include a 6,000 mm geometry whose 1:100 PDF length is 60 mm; a doorway that is open in plan but has a lintel in section; a unit-preserving exchange round-trip; a changed wall parameter propagated into a new view; and a standalone board created without installing the geometry engine.

Never mark a task successful by reducing requested detail, suppressing a failed check or changing formats without recording the loss. For repeated errors, inspect the underlying operation and preserve the working copy. First-time licensing and OS authorization constraints for future native adapters do not justify manual intermediate work in the open pipeline.

Exchange retains basic object colors, units and geometry. Procedural Cycles textures, full optical shaders, modeling history and application-specific constraints do not transfer into all mesh formats. The BLEND file preserves the rendering scene; STEP preserves exact solids. In a composed board's SVG, imported PDF lettering may become outlines; retain the separate drawing/diagram SVG sources for text editing.

`audit` additionally reads the saved BLEND meshes in Blender, checks every named mesh component against the source scene, and compares DXF projection paths with their saved model-derived geometry. It does not infer success from a render log alone. Runtime versions and execution errors are retained in module run records.
