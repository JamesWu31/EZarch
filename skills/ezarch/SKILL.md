---
name: ezarch
description: Design and produce precise architectural drawings, parametric models, Blender renders, architectural diagrams and presentation boards with open tools. Use for architectural design briefs, reference-based reconstruction, model-derived plans/elevations/sections, editable CAD exchange and automated architectural board layout.
---

# EZarch

Deliver the architectural result the user selected. Modules are independent; a request for a render or a board does not authorize redesigning the whole building.

Supported release platforms: Windows and macOS. Phase one uses open tools. Native Rhino, SketchUp and AutoCAD automation and IFC are deferred. File exchange is available without operating those applications: DXF for AutoCAD, 3DM plus exact STEP for Rhino, DAE for SketchUp. Do not claim native DWG/SKP authoring or target-application verification when those applications were not used.

## Start from the requested outcome

| Request | Read | Execute |
|---|---|---|
| Requirements, layout design, reference interpretation | [Design and reference](references/design-reference.md) | `brief`, `reference` and AI design work |
| Plans, elevations, sections, details | [Geometry and drawings](references/geometry-drawings.md) | `draft` / `views` |
| Create or change an architectural model | [Geometry and drawings](references/geometry-drawings.md), [Project data](references/project-data.md) | `model` |
| Render an existing model | [Rendering](references/rendering.md) | `render` |
| Functional, circulation, massing or area diagrams | [Diagrams and boards](references/diagrams-boards.md) | `diagram`; model views when needed |
| Layout a board or fill a template | [Diagrams and boards](references/diagrams-boards.md) | `board` |
| Format conversion or quality review | [Exchange and verification](references/exchange-verification.md) | `exchange` / `audit` |

Read only relevant references. For custom procedural geometry, use the installed CadQuery/Blender APIs and keep the resulting script with the project; the supplied rectangular/cylindrical/extruded building components are a starting library, not a limit on design form. Do not approximate a requested curved building as unrelated boxes merely to fit a helper.

## Prepare and execute

Resolve this skill directory from the location of this file, not the current working directory. First inspect `scripts/run.py doctor`. If the local runtime is missing, invoke the platform bootstrap:

```text
macOS:   sh <skill>/scripts/bootstrap.sh --profile core|model|draft|render|all
Windows: powershell -File <skill>/scripts/bootstrap.ps1 -Profile core|model|draft|render|all
```

`model` and `draft` include the exact geometry engine. `render` prepares Blender. `core` covers reference, data-driven diagrams and board composition. Reuse prepared environments. The first CadQuery import on macOS can take several minutes while binary libraries initialize; inspect progress before diagnosing a hang, then reuse that environment.

Run commands using the skill's `.venv/bin/python` on macOS or `.venv/Scripts/python.exe` on Windows, invoking `scripts/run.py`. Its input and output paths must be explicit. Example:

```text
<python> <skill>/scripts/run.py model <project.yml> --out <project>/outputs/model
<python> <skill>/scripts/run.py views <project.yml> --only ground-plan section-a --out <project>/outputs/views
<python> <skill>/scripts/run.py render <scene.json> --camera courtyard --quality preview --out <project>/outputs/render
<python> <skill>/scripts/run.py board <board.yml> --out <project>/outputs/board
```

The agent handles setup, intermediate formats and exports. Ask for design information that changes the result; do not ask the user to copy scripts, run shell commands or convert intermediate models.

## Preserve architectural intent and traceability

- Keep all real project inputs, scripts, generated models and renders in the user's project workspace, outside the skill installation and its source repository.
- For a new design, state adopted dimensions and spatial assumptions. For reconstruction, separate observed dimensions, inferred dimensions and unknown geometry. A perspective image cannot uniquely determine invisible construction.
- Use millimetres in project geometry and real-size DXF model space. Convert to metres only at rendering/GLB boundaries. Keep origin, north, vertical datum and object IDs consistent.
- Source exact geometry and rendering meshes have different roles. Preserve STEP and project parameters; never describe a 3DM/DAE triangle mesh as an exact parametric solid.
- Generate related views from the same model version. A design edit invalidates its dependent views/renders; regenerate only what the user requested and identify stale outputs.
- Use the project's agreed font. The included FangSong-style font is not Microsoft's proprietary FangSong. Retain editable text and deliver a verified PDF with fonts handled.
- Keep reference assets and public-release examples separate. Credit project inspirations and asset sources without redistributing third-party reference photography in the skill repository.

## Quality loop

Run numerical checks, then open generated images with the available image-viewing tool. Inspect actual plans, critical stair/opening details, sections, renders and the complete board. Logs and a successful export do not replace vision.

For drawings, check geometry, line hierarchy, continuity versus intentional breaks, dimensions, font coverage, scale and crop. For renders, assess architecture, viewpoint, material scale, glazing, edges, vegetation, shadows and noise. For boards, inspect hierarchy, spacing, readable labels, image resolution and fixed drawing scales.

Correct concrete problems and re-render the affected output. Record the observed problem, change and new image used to verify the change. Do not call a visibly crude placeholder, a boxed approximation or an uninspected image "high quality". If the remaining limitation is material, describe it precisely.

## Deliver

Return the editable sources and requested PDF/images with direct file links, a short statement of verification, and any material format/precision limits. Keep verbose tool logs in the project. Do not automatically publish or upload the user's architectural files.
