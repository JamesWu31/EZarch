# 几何与二维图纸工具

精确实体可用 CadQuery/OCCT，自由网格和场景可用 Blender Python，二维 CAD 可直接用 ezdxf，图解可直接用 SVG。这些工具可以独立使用；是否共享几何、从二维建模或从模型出图，由任务决定。

## 独立二维

`ezarch.drafting.Drawing(bounds, scale, title, number)` 不依赖三维模型，可输出同源 DXF/PDF/SVG/PNG。bounds、物体坐标以模型 mm 输入；scale 为比例分母，文字和笔宽用纸面 mm。方法包括 poly、text、axis、dimension、chain、level、north、section_mark、index、leader、furniture，签名见 `src/ezarch/drafting.py`。适用符号参考见 [中国制图](chinese-drafting.md)。

Drawing 是常规技术图的便利封装。需要特殊线型、块、斜向/径向尺寸或其他字体时，可直接调用 ezdxf 创建实体、尺寸和文字样式；已有 CAD 也可保留其原图层和块结构。无需先转换成 project.yml。

## 精确实体与投影

`model <project.yml> --out <dir>` 从有限的便捷构件生成 OCCT 实体、STEP 和网格交换；该命令的参数见 [接口说明](project-data.md)。复杂几何可直接用 CadQuery 的 loft/sweep/Boolean，或用 Blender 建模，不受构件列表限制。

若要复用随库投影，可在项目 Python 中构造 `Part(id, shape, material, category)`，使用 `mesh_scene` 和 `extract_view`；也可使用其他投影方法。`views <project.yml> --only <id...> --out <dir>` 提供真实平面求交和隐藏线输出。

| 随库视图参数 | 含义 |
|---|---|
| plan 的 cut_z / floor_z | 剖切高度 / 该层投影下界 |
| section 的 axis / at | x 或 y 剖切轴和位置；x 剖看向负 x，y 剖看向正 y |
| elevation / axon 的 normal / xdir | 观察法向和图面向右向量；两者叉乘决定向上 |
| scale: 100 | 1:100；固定纸幅容纳不下时工具报错，不静默改变比例 |
| projection_min_z | 默认不投影 0 mm 以下未剖背景；地下室/地形可设合适高度或 null |
| exclude / exclude_ids | 按类别或对象决定该视图的可见内容 |
| room_labels | 按视图覆写标签位置和文字，不必改变房间几何 |

几何剖切和建筑符号是两种表达：例如门扇扫掠、楼梯折断、上方虚线不是简单实体切片能自动决定的。技术图可按图种和阶段补充，参考中的有意断线可保留；概念图可使用所需简化。二维修改也不自动成为可反向推断的三维语义。

随库模型/视图使用 mm 和真实尺寸 DXF；GLB/Blender 适配器转换为 m。这是该接口的单位约定，其他工具或数据可使用自己的单位。网格化和曲线采样容差与源数据可信精度不同。

`views` 一次会保存 DXF、SVG、PDF、PNG、几何记录和报告。它的输出集合不是用户的必交清单；需要更少或不同格式时，可选用底层 API。技术图若改变打印比例，相应比例标签也要对应实际输出。
