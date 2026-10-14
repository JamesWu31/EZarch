# Exact geometry and architectural drawings

Read [project-data.md](project-data.md). The `model` module builds valid OCCT solids and named components from the project, exports STEP and a mesh scene, and creates exchange formats. `views` performs actual plane intersections and OCCT hidden-line projection; it does not draw a separate lookalike model.

For freeform work beyond the standard components, save a project-local CadQuery script that constructs `Part(id, shape, material, category)` values, uses `mesh_scene`, and passes the same parts to `extract_view`. Keep exact shapes available for STEP export and validation. Choose lofts/sweeps/Boolean solids or Blender mesh modeling according to the geometry required; do not reduce a curved design to the box helper's limitations.

Plan: set the actual `cut_z`, visible depth and excluded categories. Elevation: supply the viewing `normal` and rightward `xdir`; up is their cross product. Section: set axis and location, check which half remains. The built-in x section looks towards negative x, y section towards positive y. For an arbitrary cut, use the same OCCT plane/clip pattern in a project script and record the plane explicitly.

Inspect cut poche, doors and windows, roof lines, stairs, furniture and annotations. A geometric projection still needs architectural semantics; add measured opening/door-swing annotations and explicit stair break rules when required. Do not "repair" an intentional break found in a reference.

Model space uses mm at 1:1. View `scale: 100` means 1:100. Fixed paper sizes fail if the model does not fit, rather than silently scaling. The PDF scale bar is independently measurable. DXF uses true DIMENSION entities calculated from the same endpoints. Dimensions and external annotation updates must be regenerated after edits; no blanket claim of associative CAD constraints.

Output: each view has DXF, SVG, vector PDF, PNG preview, geometry JSON and a report. Keep source IDs in geometry records, and inspect local details at a useful resolution. For supplied 2D CAD, inspect units/layers/blocks with ezdxf, use existing entities where possible, and keep any inferred extrusion heights explicit.

Sections suppress uncut background geometry below the 0 mm ground datum by default while preserving genuinely cut foundations and basins. For a basement / uneven terrain drawing, set `projection_min_z` to the appropriate elevation or `null` to retain all projected underground geometry; model and annotate the earth boundary explicitly. This is a drawing convention, not a change to the source solids.

## 图纸表达与实体投影的边界

楼梯在平面中的截断线、上/下箭头、剖切上方虚线应按视图语义补画；水平实体切片
可能产生大黑块，不能直接当作合格的楼梯平面。保留台阶连续性与真实踏步数量，
仅在有依据的截断处断开。门扇转向、双扇门、门窗编号及表格也来自同一洞口参数。

建立楼层时同时给出 `level`、`floor_z`、`cut_z`，房间与流线明确所属楼层。
`diagram --level L1` 只出选定楼层，拒绝默认叠放多层空间。

对杆件、书籍、植物等细节按出图尺度定义可见性。复杂隐藏线运算先测试局部；
允许明确排除无助于该比例表达的零件，但不得删掉承重构件、主要栏杆或洞口来掩盖错误。
排除细杆后仍须补齐该视图所需的栏杆示意和标注。真实模型保留完整几何。

单张平面可用 `room_labels: {room_id: {position: [x, y], text: 标签}}` 调整房间图注，
避免把同一标签位置强加给所有视图。分层尺寸链应指向本层实际边界；详图须画出被尺寸引用的
平台、洞口等实体，不能只在文字中说明。仅标注改动也要绑定样式/脚本来源并重新检查版面。
