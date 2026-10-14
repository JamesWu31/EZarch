---
name: ezarch
description: Design, reconstruct or develop architectural drawings, models, interiors, diagrams, renders and boards from a brief, reference images or existing files. Use for one selected module or a requested combination, with editable programmatic outputs and architectural quality review.
---

# EZarch

完成用户选定的建筑任务。支持创作、深化、复现；可从文字、照片、草图、二维图、模型或截图开始。不要把参考样例的建筑类型、风格、构件、图量或版式变成所有项目的默认答案。

发布平台为 Windows/macOS。开放工具路线：CadQuery/OCCT、ezdxf、Blender、SVG/PDF。Rhino、SketchUp、AutoCAD 原生控制和 IFC 暂缓。交换为 DXF、3DM 网格与精确 STEP、DAE；导出成功不等于已在目标软件验收。

## 先界定本次成果

阅读 [任务与设计](references/design-reference.md)，在项目写简短 `task.yml`：所选模块、创作/深化/复现、用途与深度、输入依据、设计采用值、所需成果及完成条件。AI 编写，不要求用户填表或转换文件。只询问影响结果且无法合理决定的问题。

读取输入再决定前置步骤。单张二维图不强制建立整栋模型；已有模型渲染不授权重设计；仅排版不擅改图纸。必要时补建局部数据，记录范围。资料缺失可由设计决定补足，不能冒称实测。完整方案不能自降为体量演示。

## 按模块读取

| 本次任务 | 指引 | 可执行支持 |
|---|---|---|
| 解读参考、提出/深化方案 | [任务与设计](references/design-reference.md) | `reference`、`brief` 与项目脚本 |
| 场地、区位、交通、环境分析 | [场地与分析](references/site-analysis.md) | 数据处理、`ezarch.analysis`、SVG/PDF |
| 功能布局、室内与空间设计 | [空间与室内](references/spatial-design.md) | 尺度/邻接/使用空间检查，项目设计脚本 |
| 二维绘制、平立剖、详图 | [几何与图纸](references/geometry-drawings.md)、[中国制图表达](references/chinese-drafting.md) | `draft` / `views`、`ezarch.drafting` |
| 三维建模、图模联动 | [项目数据](references/project-data.md)、[几何与图纸](references/geometry-drawings.md) | `model`、完整 CadQuery / Blender API |
| 剖切轴测、爆炸、功能/技术图解 | [分析图与图板](references/diagrams-boards.md) | 模型视图、矢量脚本；`diagram` 仅为基础图表 |
| 渲染、镜头与材质 | [渲染](references/rendering.md)、[公开三维资源](references/public-assets.md) | `render`、项目级 Blender 脚本 |
| 排版、套用参考模板 | [分析图与图板](references/diagrams-boards.md) | `board`、Canvas / SVG |
| 格式转换 | [交换与校验](references/exchange-verification.md) | `exchange`、`audit` |

只加载相关模块。随库助手是可组合基础，不限制形态或输出类型；可直接调用完整 API，并把扩展脚本保存在项目。不要迁就有限图元或模板简化设计，不用占位图冒充未实现功能。

## 环境与资源

从本文件确定 skill 路径。使用 `.venv/bin/python`（macOS）或 `.venv/Scripts/python.exe`（Windows）。运行 `scripts/run.py doctor`；缺环境时按需执行：

```text
macOS: sh <skill>/scripts/bootstrap.sh --profile core|model|draft|render|all
Windows: powershell -File <skill>/scripts/bootstrap.ps1 -Profile core|model|draft|render|all
<python> <skill>/scripts/run.py views <project.yml> --only plan-l1 section-a --out <project>/outputs/drawings
<python> <skill>/scripts/run.py render <scene.json|blend|glb> --camera all --out <project>/outputs/render
<python> <skill>/scripts/run.py board <board.yml> --out <project>/outputs/boards
<python> <skill>/scripts/run.py review <quality.yml> --out <project>/outputs/review
```

`core` 支持参考、分析图、排版与验收；`model`/`draft` 包含精确几何；`render` 准备 Blender。复用环境；首次 macOS CadQuery 导入可能较慢，先看进度。

三维素材从公开可程序读取下载的来源按项目选取。skill 只提供入口和方法，不捆绑模型、不依赖个人素材库、不固定资产清单；下载是项目依赖。二维符号、参数化图块和样式可入库，区分标准依据与表现惯例。

## 共同数据与表达

- 几何使用 mm 和真实尺寸 DXF，明确坐标、北向、标高、楼层和稳定 ID。GLB/Blender 边界转换为 m。
- 精确几何、图纸符号和渲染细节分别表达，同一对象共享关键尺寸与位置。高面数模型不直接充当家具平面图块。
- 模型变化使关联输出过期；只重建所选成果。外部二维修改需要语义解析，不保证任意线条自动双向关联。
- 观测、推断、设计采用、计算结果分别记录；无输入和求解过程的箭头图不能称性能模拟。
- 项目输入、下载资源、脚本、模型、图纸和质量证据留在独立项目目录。

## 四项验收分别判断

阅读 [成果质量](references/quality-review.md)，建立随任务变化的检查项：**规范性、完整性、设计合理性、表现质量**。同时运行技术审计。单位、比例、文件和数量检查不能替代建筑或视觉验收。

打开实际图像：整图判断信息组织，局部判断门窗/楼梯/标注、材质和家具，再看完整图板及打印字号。参照同类型、相近表达深度的成果，记录观察、缺陷、修改及最终证据。不能仅写“简洁、统一、留白好”。饱满指信息充分、使用与构造完整、阅读有层次，不按塞满页面或图量计分。

需要修改就继续设计并重出受影响成果。严重缺项、占位家具、不可用空间、关键标注缺失、未检查图像或过期证据不能通过。`review` 仅检查证据结构与文件版本，设计/审美结论需要真实审阅。专项分析或规范核验未完成时如实保留，不用概念表达冒充。

## 交付

交付可编辑源文件、PDF/图像、资源出处、实际质量结论及具体边界。技术图标比例和单位；仿宋选择与字形覆盖均检查。图片放大或 AI 重绘不能修复几何事实。未经请求不发布项目。支持与实测平台、目标应用验收情况分别说明。
