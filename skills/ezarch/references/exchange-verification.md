# 工作格式、行业交付与转换边界

用户的正常输入可以是 DWG/3DM/PDF/图片/链接与文字需求。工作中选择 DXF、原生3DM对象、OCCT精确几何、Blender、SVG或其他数据，由 AI 根据操作决定。输出按本次用途满足行业查看和后续编辑习惯；不要求用户处理转换，不要求每次全格式交付。

| 路线 | 当前能力及边界 |
|---|---|
| DWG ↔ DXF | 可选 ODA File Converter 双向转换；ezdxf 编辑完整工作 DXF。保留源文件与所选版本，不自动 repair。代理对象、外参、字体与专有编辑语义不能笼统保证无损 |
| 原生 3DM | rhino3dm 读取/写回精确曲线、曲面、BRep、拉伸体和网格，UUID/属性/图层可保留。能读不等于具有完整 Rhino 几何内核 |
| OCCT → 3DM 精确路线 | `model --formats 3dm` 对直边等截面拉伸实体生成闭合 BRep，保留对象名称/分类及洞口边界；使用原生封闭拉伸生成精确平面BRep。其他实体拒绝，不静默离散 |
| 直接创建精确 3DM | 原生 rhino3dm 曲线、NURBS曲面、解析BRep、带孔拉伸体；`write_geometry` 可写任意受支持原生对象。复杂裁剪曲面/布尔按实际库能力处理 |
| STEP | CadQuery/OCCT 的精确实体/曲面交换，可导入 Rhino继续编辑；不是参数历史。通用 3DM↔STEP 曲面转换未作为已实现能力 |
| 网格 3DM | `exchange scene.json --formats 3dm` 保持原网格语义；与 model 的精确实体出口不同，不能替代需要曲面/实体编辑的交付 |
| DAE | 网格节点/基本颜色，供 SketchUp导入；随库毫米、Z_UP。没有原生SKP/材质完整保真承诺 |
| GLB/GLTF | 网格、节点及适用PBR材质；随库毫米→米、Z向上→Y向上变换；不带CAD参数历史 |
| BLEND | 场景、对象、修改器、相机、着色器及可打包图像；外部库/插件/缓存仍需查依赖 |
| SVG/PDF/图像 | SVG保留矢量对象、文字和分组；PDF面向出图，图片面向预览/表现。不能仅靠PDF代替可编辑CAD模型 |

## DWG 操作

`convert <source.dwg|dxf> <target.dxf|dwg> [--version ACAD2018] [--repair]` 使用独立临时输入目录，仅处理选定源文件。输出已有时拒绝覆盖；repair 是显式修复操作，不是默认。`inspect`/`edit` 可直接接收 DWG，由工具建立工作副本。跨格式的对象对应需核对，不能假定全部 handle 永远不变。

ODA 官方提供免费的闭源 File Converter，支持 macOS/Windows和命令行，不需AutoCAD；它不等同收费ODA开发SDK。`bootstrap --install-oda` 可按需取得外部安装包并检测，实际系统权限/许可提示可能需要处理。仓库不捆绑或重新分发安装包。`doctor`/`EZARCH_ODA` 可发现或指定程序。

[官方转换器](https://www.opendesign.com/guestfiles/oda_file_converter)、[免费应用说明](https://www.opendesign.com/guestfiles)、[ezdxf odafc](https://ezdxf.readthedocs.io/en/stable/addons/odafc.html)。ezdxf核心不支持DWG，其 addon 仍调用外部程序。

## 回读、比较与交付可用性

文件可解析、外观一致、几何/精度一致、特殊对象可编辑是不同验证。按受影响内容比较关键实体、曲线/块/填充、尺寸/文字、布局、图层、外部依赖、坐标和实际输出视图；数目或包围盒相同不足以证明转换完整。数值容差依据单位和任务精度确定，不用统一宽松阈值掩盖变化。

`inspect/query/compare` 为原始文件提供版本绑定查询；`audit <file|directory|project.yml> --out <dir>` 为文件回读或随库输出关系检查。随库只生成所选格式，不要求无关同名配套文件；项目比对可用 `--outputs`。二者不判断设计、美感、全部技术合规或目标软件行为。

开放库回读、转换回转、在 AutoCAD/Rhino/SketchUp 中实际打开继续编辑分别记录。未做商业软件验收时如实说明；不能从扩展名推断已通过。用户再次提供修改后的文件时，以新版本为依据接续工作。

技术依据：[rhino3dm](https://github.com/mcneel/rhino3dm)、[BRep API](https://mcneel.github.io/rhino3dm/python/api/Brep.html)、[CadQuery交换](https://cadquery.readthedocs.io/en/latest/importexport.html)、[glTF单位与坐标](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units)。原生商业应用控制、SKP写入和IFC仍暂缓；DWG/3DM文件适配不随之暂缓。
