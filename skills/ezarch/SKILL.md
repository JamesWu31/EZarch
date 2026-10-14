---
name: ezarch
description: Tool guidance and optional infrastructure for creating or editing architectural drawings, models, diagrams, renders and layouts programmatically. Consult for ezdxf, CadQuery/OCCT, Blender, SVG/PDF, file exchange and applicable drafting conventions.
---

# EZarch

帮助 AI 用程序化工具实现用户要求的建筑与空间表达。用户需求、参考内容及其使用意图决定目标；模型判断设计、分析、表达、工具组合和工作安排。工具的默认值、例子和封装能力不决定成果的类型、风格或深度。

模块供按需查阅，可以独立使用或组合。沿用现有项目、直接调用原生 API、修改辅助代码或另写脚本均可；不要求任务表、统一数据模型、固定流程、图量或交付包，也无需为未使用封装补写理由。具体接口的字段和单位只约束该接口。

列出的工具、网站与方法是起点，不是完整清单或优先顺序。根据任务可主动联网查其他资料、资源和官方接口，选用其他适合的程序化方法。

## 工具入口

| 当前需要 | 查阅内容 |
|---|---|
| 准备或排查环境 | [Windows/macOS 按需安装](references/environment.md) |
| 读取 PDF、图片参考 | [参考读取与尺度](references/design-reference.md) |
| 新建 CAD、精确实体、平立剖 | [几何与图纸](references/geometry-drawings.md) |
| 修改已有 DXF/SVG/BLEND，二维三维衔接 | [原生操作例子与局部修改](references/edit-existing.md) |
| 技术图纸的表达依据 | [中国制图参考](references/chinese-drafting.md) |
| 地图、统计、环境或使用空间计算 | [地图与分析参考](references/site-analysis.md)、[空间测量](references/spatial-measurement.md) |
| SVG、分析图、图表或版面 | [矢量与排版](references/diagrams-boards.md) |
| 材质、灯光、相机或素材 | [Blender 渲染](references/rendering.md)、[公开素材入口](references/public-assets.md) |
| 格式转换、单位、文件回读 | [交换与检查](references/exchange-verification.md) |

技术规范按地区、图种和阶段选用；模型依据本次要求判断设计、内容和视觉效果。运行成功、文件能打开或数值检查通过，只说明相应工具实际验证的事项。

随库构件命令需要参数时，查 [project.yml 接口](references/project-data.md)。它是便捷工具的输入格式，可直接用原生几何或项目自己的数据替代。

## 基础设施范围

提供 Windows/macOS 的开放工具环境、字体及轻量二维符号。Rhino、SketchUp、AutoCAD 原生控制和 IFC 暂缓；开放格式可提供 DXF、精确 STEP、网格 3DM/DAE 等，编辑能力见格式说明。

三维素材按项目从公开可读取下载的来源获取；skill 不捆绑模型库或依赖个人素材目录。用户提供的模型和其他资料可直接使用。资料、素材与成果保存在项目中，仓库开发验证在库外进行。
