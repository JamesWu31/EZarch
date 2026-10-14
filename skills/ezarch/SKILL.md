---
name: ezarch
description: Tool guidance and optional infrastructure for programmatic architectural drawings, models, spatial diagrams, renders and layouts. Consult for ezdxf, SVG/PDF, CadQuery/OCCT, Blender, file exchange or applicable technical drawing conventions.
---

# EZarch

为 AI 提供建筑与空间表达的工具知识、基础设施和适用制图规范。用户需求、参考内容及其使用意图决定目标；模型结合这些信息自主判断设计、分析、表达、工具组合和工作安排。本 skill 的流程建议、样例、样式和辅助脚本不优先于用户要求。

模块是可选能力，不是执行阶段。可以只查一个参数、沿用现有项目、直接调用原生 API、编写自由 SVG 或采用其他适合任务的程序化方法。使用本 skill 不要求创建 task.yml/project.yml/quality.yml，不要求固定步骤、图量、风格、审计报告或交付包。工具选择也可以随任务进展调整。

## 按需要查阅

| 需要解决的问题 | 可用工具 / 指引 |
|---|---|
| 准备或排查运行环境 | [按需安装](references/environment.md)：Windows/macOS、Python、Blender |
| 从 PDF、图片读取参考信息 | [参考读取](references/design-reference.md)：文字/路径/预览、图像尺度 |
| 绘制二维 CAD、从模型出平立剖 | [几何与图纸](references/geometry-drawings.md)：ezdxf、独立 Drawing、OCCT 投影 |
| 查询技术图纸的表达规则 | [中国制图参考](references/chinese-drafting.md)：适用条件、尺寸/轴线/标高等 |
| 制作精确实体或自由三维形态 | [几何工具](references/geometry-drawings.md)：CadQuery/OCCT、Blender Python |
| 做地图、空间分析或使用尺度计算 | [场地与分析工具](references/site-analysis.md)、[空间测量助手](references/spatial-design.md) |
| 制作分析图、图表、SVG 或版面 | [矢量与排版工具](references/diagrams-boards.md)：直接 SVG、PDF、可选排版器 |
| 设置相机、材质、灯光或获取素材 | [Blender 渲染](references/rendering.md)、[公开素材入口](references/public-assets.md) |
| 导出或检查交换文件 | [格式与可选检查](references/exchange-verification.md)：DXF、STEP、3DM、DAE、GLB |

## 使用辅助代码时

随库命令是便利封装。需要它们的输入格式时查 [project.yml 接口](references/project-data.md)；需要保存检查证据时查 [可选证据检查器](references/quality-review.md)。这些接口的单位、字段和校验只约束对应调用，不限制任务采用的数据结构、坐标体系、版式或工具。封装不合适时可修改、替换或绕过，不需要为绕过补写审批、解释表或验收手续。

技术图的规范按地区、图种、阶段和用户要求选用；概念图、表现图与技术图可以有不同表达深度。附带字体、图块与模板供选用。设计和视觉判断仍由模型依据本次要求完成，检查工具只能证明其实际检查的事项。

## 分发范围

本仓库准备 Windows/macOS 的开放工具环境；Rhino、SketchUp、AutoCAD 原生控制及 IFC 适配暂缓。现有交换工具可生成 DXF、精确 STEP、网格 3DM/DAE 等，具体信息损失见格式说明。

三维素材按项目从公开可读取下载的来源获取，skill 不捆绑模型库或依赖个人素材目录。项目资料与成果放在用户项目中；仓库开发验证在库外进行。以上是本库的资源和维护边界，不规定使用者的设计流程。
