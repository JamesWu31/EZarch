# SVG、分析图与排版工具

图形内容、风格、布局、字形、图量和叙事由用户需求、参考和模型判断决定。可直接生成或修改 SVG，沿用现有脚本/模板，或选用下面的工具。没有必须先写分析问题、建模型、套槽位再出图的步骤。

## 直接 SVG

SVG 可承载地图、统计图、关系图、技术线稿和自由图板。数据可以是 JSON/CSV、图像坐标、地理数据、现有矢量或临时计算结果，无需建筑 project.yml。原生 SVG 支持路径、任意角度文字、文字沿路径、分组、clipPath、渐变等；语义图层、独立样式和译名表可以帮助后续编辑，但不规定项目组织方式。

需要可编辑文字时，可保留 text 元素；转曲适合某些交付要求，但会失去文字编辑性。SVG 的 viewBox 坐标与纸面 width/height 可分开，图像坐标不必换成 mm。PDF/PNG 可经项目已有渲染器导出，或使用兼容的 SVG/浏览器工具；不同渲染器对字体、滤镜、裁剪的支持可能不同。

## 简单画布与房间图例

`ezarch.graphics.Canvas(width_mm, height_mm, font=None)` 提供 poly/line/rect/circle/text/text_box/image/pdf/save，可直接从 Python 生成 SVG/PDF/PNG，不需要项目模型。API 见 `src/ezarch/graphics.py`。

Canvas 支持任意角度文字；font 可指定项目字体文件，省略时使用随库仿宋和 Helvetica 系列。`save(stem, formats=["svg"])` 可仅输出所需格式。它不提供完整 SVG/CSS 能力；富文本、滤镜等可直接使用 SVG 或其他库。自定义字体的许可与交付依赖由所选字体决定。

`diagram <project.yml> --level <id> --out <dir>` 只是已有房间多边形的功能/概念路线/虚实/面积绘制器。它不能替代任意分析图；地图或统计图不必转换成房间。若调用这个命令，多楼层数据需要 level 参数以选择本次输入。

## 可选 board 排版器

`board <board.yml> --formats pdf --out <dir>` 接收独立模板，无需建模。适合 PDF/图片和简单文字、线框的纸面合成；可用用户现有版式或直接编写 SVG 代替。

```yaml
sheets:
  - size_mm: [594, 420]
    background: '#ffffff'
    items:
      - {type: text, x: 20, y: 25, text: 'TITLE', size: 8}
      - {type: pdf, file: plan.pdf, x: 20, y: 45, w: 260, h: 270, scale_lock: true}
      - {type: image, file: view.png, x: 300, y: 45, w: 270, h: 180, minimum_ppi: 150}
```

该示例仅说明参数，不是推荐的版式或图量。路径相对模板；x/y/w/h 是纸面 mm。sheet.font 可指定字体文件，文字 rotation 为角度。type 支持 text、line、rect、pdf、image，不直接导入 SVG 元素。带 w/h 的 text 使用有界换行；未指定宽高的 text 为逐行定位。`allow_overlap: true` 允许有意叠放，否则工具会拒绝媒体槽位/文本框碰撞。

`scale_lock` 对 PDF 槽位要求物理比例不变；可不启用，但图纸标注的比例仍需与实际缩放一致。图片保持宽高比，minimum_ppi 根据放置尺寸检查有效像素。固定槽位算法不会自动决定优秀的版式。

formats 选择 SVG/PDF/PNG；选择 PDF 时同时生成合订 presentation.pdf，并附带布局报告。PDF 槽位在合成 PDF 中保持矢量，但转入 SVG 时文字会转曲。需要保留原 SVG 文字/图层时，可直接组合 SVG，不必经 PDF 槽位。PDF/X、CMYK 等是另行配置的印前能力，不包含在默认输出中。

## 三维图解的可选表达

模型投影、隐藏线、Blender 正交渲染与自由矢量都可用于轴测/爆炸，选择取决于所需精度和风格。用分组展示位移可保留原模型；概念分解也可直接画 SVG。复杂相交面按平均深度排序可能出现穿透，真实深度缓冲或隐藏线算法可解决这类遮挡问题。网格精细度、材质和标签可按图面需要处理，没有必须采用的镜头组或表现形式。

局部改字与 SVG 组合要点见 [原生操作](edit-existing.md#svg保留图形仅修改指定文字)。
