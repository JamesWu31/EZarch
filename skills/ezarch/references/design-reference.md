# Design and reference intake

Run `reference <image-or-pdf> --out <dir>`. PDF intake extracts all pages, text and vector paths and renders previews; image intake preserves pixel dimensions. Optional `--known-mm N --pixel-distance P` records orthographic scale from a known distance. These are extraction tools, not claims of semantic recognition.

Open relevant previews. Identify boundaries, openings, circulation, level heights and viewpoints. For PDF paths account for page transforms, clipping and intentional dotted/dashed lines. A zero-length round-cap stroke may represent a meaningful dot. Inspect stairs and tiny symbols separately rather than trusting an overall image difference metric.

For image calibration, record the two actual source-pixel endpoints and what real distance they represent in the project's source notes. Do not use distances measured on a resized preview as if they were source pixels. Rectify scanned perspective before applying a single scale; perspective photos require camera/vanishing-point reasoning and corroborating dimensions.

For a design without a traceable drawing, begin with a functional/area brief, adjacency and circulation, orientation, structural intent, levels and hard dimensions. Separate net room areas from gross area. Resolve circulation and opening conflicts before adding presentation detail. Offer alternatives only when useful to the user's requested design decision.

Write the chosen parameters into `project.yml` using [project-data.md](project-data.md), run `brief`, and inspect room areas and overlap results. A failed overlap check is a design issue to resolve, not something to hide by disabling the checker. Specialized regulatory or performance claims require a stated source, jurisdiction/method and corresponding verification.

Partial elevations/sections may be drafted directly when adequate measured information is available; construct a full model only when it helps deliver the selected scope. With partial references, mark designed or inferred parts rather than asserting perfect reconstruction.
