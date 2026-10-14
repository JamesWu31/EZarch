# Blender 渲染操作

直接用 bpy 可创建或修改几何、材质、灯光、相机和渲染配置。[原生修改例子](edit-existing.md#blender保留场景只改选定对象) 演示沿用用户场景。相机、细节和画面风格由任务决定。

## 随库入口

`render <input> --camera <name|all> --out <dir>` 接收 BLEND/GLB/GLTF/OBJ/PLY/STL 或 EZarch scene.json。OBJ/PLY/STL 需 `--source-units mm|m`。输入为 BLEND 时默认保留引擎、采样、色彩管理、曝光、透明背景、分辨率、图像格式、灯光及原相机名称；输出写到指定目录。

`--width` 和 `--samples` 只覆盖相应设置。`--quality preview|final` 是显式的分辨率/采样预设；已有 BLEND 不传它就沿用场景。新导入的裸模型使用 Cycles/AgX 与预览默认值，可在脚本中改写。中文及含特殊字符的相机使用可移植文件名映射，不重命名场景对象。

默认保存渲染图和 scene.blend 副本；`--no-save-blend` 仅渲染，不保存场景副本。已有场景沿用图像文件格式（例如 PNG/JPEG/EXR）；视频配置需要先在 bpy 中设为本次需要的静态图像格式。无论是否保存副本，都有轻量执行记录。

## 可复用操作

- `scripts/blender_scene.py` 提供材质、资产导入、灯光、相机与设备选择函数，适合按当前需求取用。
- scene.json 入口把 mm 转为 m；已有 BLEND 保留其坐标与单位。网格和素材的原点、尺度、朝向决定是否对齐。
- PBR 的贴图重复尺度、法线和色彩空间影响材质表现。随库 `texture_size_m` 为米制；自定义着色器可直接使用节点 API。
- Cycles 采样、降噪、反弹次数和分辨率影响成像；真实细节仍来自几何、材质、光照和构图。打印像素可由最终放置尺寸与目标 PPI 计算。
- 新场景可探测 CPU/GPU；已有 BLEND 保留设备设置，失败时根据日志处理，避免静默改变用户场景配置。

新生成场景保存时打包支持的图像依赖；已有 BLEND 默认保留依赖组织，需要独立交付时可主动调用 `bpy.ops.file.pack_all()`。程序材质、参数历史和第三方依赖的跨格式保留程度见 [格式说明](exchange-verification.md)。

公开素材及导入方式见 [资源入口](public-assets.md)。内置素材类别和预设不是 Blender 能力范围。
