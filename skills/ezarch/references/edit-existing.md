# 原生操作、局部修改与二维三维衔接

下面是独立操作例子；参数只说明本例的接口，可以直接复制改写。已有项目的脚本、单位和对象组织可继续使用。例子保存副本，输出位置由调用者选择。

## DXF：定位实体、修改和定比例出图

`ezdxf.readfile(path)` 保留文档的图层、块和布局。通过 `doc.modelspace().query('TEXT[layer=="LABELS"]')` 查看实体，读取 `entity.dxf.handle` 进行精确定位；同一个块定义的修改会影响全部引用，单个 INSERT 的位置/旋转修改只作用于该引用。新项目可用 `ezdxf.new("R2010")`、`doc.layers.new(...)`、`doc.blocks.new(...)` 创建实体与组织结构。

[edit_dxf.py](../scripts/examples/edit_dxf.py) 用原生 ezdxf 修改一个指定实体，另存并按给定比例输出 PDF：

```sh
python "<skill>/scripts/examples/edit_dxf.py" source.dxf edited.dxf --handle 3A --move 200 0 --pdf edited.pdf --scale 100
# 或替换指定 TEXT/MTEXT 的内容
python "<skill>/scripts/examples/edit_dxf.py" source.dxf edited.dxf --handle 4B --text "Reading room"
```

handle 示例需替换成实际文件中的值；move 使用源文件单位。绘图后端按源单位换算纸面比例，自动纸幅约留 10 mm 边距；示例补偿 ezdxf 1.4.4 PDF 后端的纸面整数点取整，避免比例漂移。固定纸幅可用 `layout.Page(width, height)`；`Settings(fit_page=False, scale=...)` 保持尺度，图形是否放得下由纸面尺寸决定。已有纸空间用相应 layout，不必重建图框。

DXF 尺寸可用 `msp.add_linear_dim(...).render()`；对齐、角度和半径尺寸使用对应 API。移动构件后，相关尺寸的定义点、文字和剖面是否需要更新由修改含义决定；仅移动实体不会自动建立建筑关联。该 PDF 后端可输出矢量线稿，但文字可能转曲，需编辑文字时保留 DXF 或另用 SVG text。

官方操作资料：[实体查询](https://ezdxf.readthedocs.io/en/stable/tasks/query.html)、[绘图与导出](https://ezdxf.readthedocs.io/en/stable/addons/drawing.html)。版本以安装环境为准；仓库测试 ezdxf 1.4.4。

## CadQuery：自定义实体、布尔和真实剖切

[solid_section.py](../scripts/examples/solid_section.py) 独立演示 ellipse、loft、cut、section、STEP/DXF 导出，不使用 EZarch project.yml：

```sh
python "<skill>/scripts/examples/solid_section.py" --out study --width 8000 --depth 5000 --height 3600 --cut-z 1200
```

这是几何试件，不是推荐建筑形式。模型和剖面共用一次构建得到的形体，尺寸修改后重算。工程坐标可用 `Workplane(Plane(origin=..., xDir=..., normal=...))` 定义截面；STEP 导入用 `cq.importers.importStep(...)`。真实剖切提供相交几何；建筑门窗符号、标注和上方投影另外组织。

官方资料：[CadQuery API](https://cadquery.readthedocs.io/en/latest/classreference.html)、[导入导出](https://cadquery.readthedocs.io/en/latest/importexport.html)。当前环境为 CadQuery 2.8.0。

## Blender：保留场景，只改选定对象

```sh
blender --background --disable-autoexec --python-exit-code 1 --python "<skill>/scripts/examples/edit_blend.py" -- --input source.blend --output edited.blend --object "入口雨棚" --move 0 0 0.2
```

命令中的 blender 可替换为 doctor 检出的完整可执行路径；Windows PowerShell 对带空格的可执行路径使用 `& "路径"`。

[edit_blend.py](../scripts/examples/edit_blend.py) 用对象名称定位、在世界坐标平移，不重建灯光、相机或材质。move 是 Blender 场景坐标；实际长度还取决于 `scene.unit_settings.scale_length`。有父级、约束、动画或实例时，可按任务修改相应控制对象/关键帧，不能把所有可见对象当成互相独立的网格。

材质操作可通过 `obj.data.materials` 与 `material.node_tree`；共享材质、共享 mesh data 会影响其他使用者，只有需要单独变化时才复制。相机通过 `scene.camera` 指定；操作现有文件时沿用其渲染配置，具体参数也可直接通过 bpy 修改。随库 [render](rendering.md) 可渲染保存的副本。

官方资料：[Blender Python](https://docs.blender.org/api/4.5/info_quickstart.html)。例子在 Blender 4.5 验证。

## SVG：保留图形，仅修改指定文字

```sh
python "<skill>/scripts/examples/edit_svg.py" source.svg edited.svg --id map-title --text "Urban structure"
```

[edit_svg.py](../scripts/examples/edit_svg.py) 只依赖 Python 标准库，保留路径、分组、样式和坐标，对一个带 ID 的 text/tspan 叶节点替换文字。XML 序列化可能改变格式或命名空间写法；复杂富文本可直接按项目结构修改 tspan。文字长度变化后能否放进原位置需看实际图面。

新建 SVG 可直接写 XML：设置纸面 width/height 与独立 viewBox，用 group、path、text、clipPath、CSS 等表达。组合已有 SVG 时可用嵌套 svg 或组变换，重复 ID 与渐变/裁剪引用需一起改名。为了可编辑文字，无需先经过 PDF 转曲。导出采用已有浏览器/SVG 渲染器，字体就绪与打印尺寸影响结果。

## 衔接中的操作要点

二维参考或模型之间，明确当前操作使用的单位、原点、朝向和观察方向即可；记录可留在现有代码或项目文件，无需引入统一 schema。图像像素与真实长度通过已知尺度关联；透视照片不能直接套一个比例得到遮挡部位的精确尺寸，允许设计推断时由模型确定并表达假设。

模型改动可重新生成相关剖面/投影，独立标注层可继续保留并调整。二维线条本身不一定包含墙高、材料或楼层语义；从二维建立三维时，可结合其他资料或按创作要求确定。不存在普遍可逆的任意二维三维转换，也不要求所有项目先建模。
