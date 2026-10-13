# Diagrams and boards

`diagram <project.yml> --out <dir>` produces editable vector functional, circulation, solid/void and area graphics from project polygons. Use model-derived axon views for 3D relationships. Circulation is an explicit design diagram; it is not a simulated occupancy result. Sunlight/energy/wind claims require an appropriate solver and recorded inputs, otherwise label the image as a conceptual diagram.

SVG is the editable 2D expression format. PDF is generated from the same page geometry; text remains editable in SVG and fonts are handled in PDF. Data calculations happen before styling. Use consistent colors and restrained line/label hierarchy; do not replace a vector diagram with a flattened screenshot.

`board <board.yml> --out <dir>` is independent of model generation. The agent creates or adapts its physical page template; the user does not need to populate YAML. For a supplied SVG/PDF/image template, inspect it, identify usable content slots and build the slot specification. Use PDF backgrounds where appropriate, retaining their vector quality; mark overlay items `allow_overlap: true` when intentional. Other media slot intersections are rejected. Do not claim that raster backgrounds became editable vectors.

Template contract:

```yaml
title: Project presentation
preview_dpi: 100
sheets:
  - title: Architecture
    size_mm: [594, 841]
    background: '#ffffff'
    items:
      - {type: text, x: 25, y: 35, text: 'PROJECT TITLE', size: 10, bold: true}
      - {type: image, file: outputs/render/courtyard.png, x: 25, y: 55, w: 544, h: 360, minimum_ppi: 150}
      - {type: pdf, file: outputs/views/plan.pdf, x: 25, y: 450, w: 264, h: 286, scale_lock: true}
```

Files resolve relative to the template. PDF slots preserve vectors. `scale_lock` requires an unchanged physical scale; inspect the actual source PDF dimensions and allocate a matching slot. Do not force a drawing into a smaller slot while keeping its original scale label. Image slots maintain aspect ratio and enforce a minimum effective PPI.

Compose a strong reading order: one clear project statement, primary image or drawing, supporting views/diagrams, short captions, coherent margins. Avoid filling every corner. Use the generated source dimensions and actual image aspect ratios to compute slots, then inspect the whole rendered board and zoom into important labels. Check inter-slot collisions as well as page-edge overflow; fix layout parameters and regenerate, never manually patch only the exported PDF.

Final outputs include editable SVG boards, each board's PDF/PNG, a combined presentation.pdf and placement/scale/image-resolution report. PDF/X or specialist CMYK requirements need a separately verified print workflow and must not be claimed by default.
