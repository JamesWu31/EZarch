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


## 内容与设计深度

基础 diagram 命令只有房间色块/概念路线/虚实/面积示例；它不是完整分析能力。先为每张图写问题、输入与结论，再用项目脚本和 Canvas/SVG/模型视图实现。场地、交通、环境、户型、构造等采用不同表达；多层数据应分层绘制，不把楼层叠成一张。

爆炸图从稳定构件ID按层或系统分组，使用明确位移向量与引线，保存原位和展示位移；不改变原模型。剖切轴测剔除/剖开遮挡部分以显示真实空间；多轴测应互补。技术图解说明节点、构造层次和传力/排水意图，计算与概念分开。

先组织阅读顺序与有效内容，再决定页数、网格和风格；不强制某种配色或A1数量。区位—策略—空间—技术只是可选叙事。模板参考提取比例、层次与节奏，不复制参考中的图片。PDF技术图保持物理比例；缩放时必须重新生成比例及字高。重点图、局部放大、图注、材料表和数据应互相关联，不能以大标题和空白掩盖缺项。

text项可指定 w/h/size/leading，排版器按实际字体宽度换行、越界拒绝，并检查这些文本框与媒体槽位的碰撞；不会自动把文字缩小。无w/h的旧式逐行text只作页边界检查，仍需人工视觉复核。故意叠加用 allow_overlap:true 并检查阅读效果。

矢量轴测不宜直接输出渲染级圆角家具的数十万三角面。主体保留精确几何，对展示中的曲面用明确、可测的简化精度；记录范围与偏差，不能改变尺寸模型。纸面无法辨认的细节不应拖慢每次出图。

复杂剖切轴测优先使用真实深度缓冲/隐藏线求解。按三角形平均深度排序的画家算法会在大面相交时产生穿透和对角裂面，不能当作最终结果。可用 Blender Workbench/Cycles 正交图层，再以 SVG/PDF 添加矢量图注与数据；注明混合图像，不能称全矢量。检查相机宽高比，尤其竖版爆炸图不能裁掉两侧构件。
