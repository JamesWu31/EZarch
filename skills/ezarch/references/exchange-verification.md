# 格式交换与文件检查

| 格式 / 工具 | 保留内容与边界 |
|---|---|
| DXF / ezdxf | CAD 图层、文字、块、填充和尺寸；字体可另行提供 |
| STEP / CadQuery | 精确实体与曲面，不包含原参数建模历史 |
| 3DM / 随库 rhino3dm 交换器 | 有名称、分类和基本颜色的网格；精确几何可另用 STEP |
| DAE / pycollada | 网格、构件节点、基本颜色；随库声明毫米、Z_UP |
| GLB | 网格及场景，随库适配器用 m、Y 向上，并写入从建筑 Z 向上的变换 |
| BLEND | Blender 场景、灯光、着色器及可打包的图像依赖 |

AutoCAD 交换使用 DXF；Rhino 根据编辑需求选择网格 3DM 或精确 STEP；SketchUp 使用 DAE。第一期原生 DWG/SKP 写入、商业软件控制和 IFC 暂缓。开放库回读验证和在目标软件打开验证是不同证据；材质、图层、尺寸语义及编辑能力取决于实际格式与导入设置。

## 选择输出

```text
model project.yml --formats step --out model
model project.yml --formats scene glb --out render-input
views project.yml --only section-a --formats dxf pdf --out sheets
board board.yml --formats pdf --out boards
exchange scene.json --formats dae --out exchange
```

model 默认仅 STEP；明确列出需要的格式。scene 是供随库渲染/跨格式比较使用的 JSON，可单独选用。views/Drawing/Canvas/board 的 formats 参数选择相应输出；省略时保留多格式便利默认值。已有同名旧输出不会因本次未选择而被删除，读取本次报告或使用独立输出位置可区分。

模型使用 `generate_model(project, out, formats=[...])`，独立绘图使用 `drawing.save(stem, formats=["dxf"])`。直接原生 API 无需产生随库报告。

## 文件回读

`audit <file|directory|project.yml> --out <report-dir>` 是可选技术检查。

- 单文件支持 DXF、STEP/STP、GLB/GLTF、3DM、DAE、PDF、SVG，检查能否回读及相应结构；不要求同名配套文件、固定目录或毫米单位。
- 随库目录可按已声明的输出核对文件是否缺失、部分几何与单位是否对应、引用文件是否更新。图纸只输出 PDF 时不会要求 DXF；模型只输出 GLB 时不会要求 STEP/3DM/DAE。
- `audit project.yml --outputs <actual-directory> --out <report-dir>` 额外比对源版本；省略 outputs 保留旧版同级 outputs 的查找约定。
- 目录没有随库报告时，对支持的文件做独立回读。自定义检查也可直接用各工具原生 API。

数值、可读性和文件版本检查不判断构图、美感、建筑合理性或用户任务是否完成。检查具体几何、实际打印比例或视觉效果时，可量测对应对象、查看导出图像或与用户参考比较，不需要建立统一验收表。

GLB 的米制与 Y 向上依据 [glTF 坐标系](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units)。0.4 修复了旧交换器只换单位、没有换轴的问题；旧版本文件需重新导出或按其实际坐标适配，不能只检查原始顶点包围盒。
