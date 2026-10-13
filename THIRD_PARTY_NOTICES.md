# Third-party notices

EZarch's own code is AGPL-3.0-or-later. Dependencies are obtained by the installer, not vendored as binaries in this repository. Consult each installed distribution's license for complete terms.

| Component | License / role | Upstream |
|---|---|---|
| PyMuPDF / MuPDF | AGPL-3.0 open-source option (commercial option also offered); PDF/vector operations | https://pymupdf.readthedocs.io/ |
| CadQuery | Apache-2.0; exact modeling API | https://github.com/CadQuery/cadquery |
| OCCT / cadquery-ocp | OCCT LGPL-2.1 with additional exception; Python bindings distributed separately | https://dev.opencascade.org/resources/licensing |
| Blender | GPL-3.0-or-later application; separately downloaded from official distribution | https://www.blender.org/about/license/ |
| ezdxf | MIT; DXF | https://github.com/mozman/ezdxf |
| rhino3dm | MIT; openNURBS interchange | https://github.com/mcneel/rhino3dm |
| trimesh | MIT | https://github.com/mikedh/trimesh |
| pycollada | BSD | https://github.com/pycollada/pycollada |
| Shapely | BSD-3-Clause; includes GEOS notices in its distribution | https://github.com/shapely/shapely |
| Pydantic / PyYAML / fontTools | MIT | https://pypi.org/ |
| Pillow | MIT-CMU | https://github.com/python-pillow/Pillow |
| NumPy | BSD-3-Clause plus bundled dependency notices | https://numpy.org/doc/stable/license.html |
| uv | MIT / Apache-2.0 | https://github.com/astral-sh/uv |

## Included font source and derivative

`assets/fonts/FandolFang-Regular.otf` is the original Fandol 0.3 font. Its upstream COPYING, README and source attribution accompany it. It is distributed under GPL with the upstream font embedding exception. `EZarchFang.ttf` is a renamed TrueType-outline derivative produced by `scripts/build_font.py`; retain the same notices. Both source and build script are included. No Microsoft or other proprietary FangSong font is bundled.

## Architectural references and user outputs

Real architectural precedents and photographs remain in the user's separate project workspace with source attribution. They are not part of the EZarch distribution. Project-specific models, renders and diagrams are not packaged as skill examples. Nothing in this notice transfers ownership of user-authored architectural content to EZarch.
