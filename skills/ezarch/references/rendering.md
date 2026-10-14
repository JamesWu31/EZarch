# Blender 渲染工具

相机数量、画面风格、细节程度和制作顺序由用户要求与模型判断决定。可直接使用 Blender Python 操作用户已有场景或自行建模；随库 render 命令是可选入口，预览/最终参数也是选项。

## 可选命令

`render <input> --camera <id|all> --quality preview|final --out <dir>` 接收 BLEND/GLB/GLTF/OBJ/PLY/STL，或 EZarch scene.json。可用 `--width`、`--samples` 覆盖成像参数。OBJ/PLY/STL 入口需要 `--source-units mm|m`，因为这些输入本身通常不能可靠说明单位。原生 SKP/DWG 和任意 NURBS 3DM 的随库导入暂缓。

scene.json 入口把建筑毫米坐标转为 Blender 米制，配置材质、灯光和相机。独立 BLEND 使用其已有场景，不必先生成建筑 project.yml。自定义模型、非写实材质和正交视图均可直接用 bpy 实现；不受随库预设类型限制。

## 操作提示

- `scripts/blender_scene.py` 提供材质、公开资产导入、灯光、相机和设备选择函数，可单独复用或替换。
- 几何模型、网格和外部资产可能采用不同单位、原点和朝向；导入变换决定它们能否对齐。资产入口见 [公开素材](public-assets.md)。
- PBR 的纹理重复尺度、法线和色彩空间影响物理材质表现；`texture_size_m` 是随库材质的米制参数。自定义着色器可有自己的表达方式。
- Cycles 采样、降噪和分辨率控制成像，不能改变几何关系。需要打印时，可由版面尺寸和目标有效 PPI 反算像素。
- 预览小图适合快速判断相机和材质；已有可靠场景也可直接渲染目标成果。CPU/GPU 可通过工具实际检测，不要求采用固定后端。

该命令会保存 PNG、BLEND 和执行记录；实际交付格式按任务选择。`bpy.ops.file.pack_all()` 可将支持的外部图像打包进 BLEND，适合需要独立交付场景时使用。程序材质、文件路径和第三方依赖是否被保留，取决于具体导出格式；简单网格交换不会保留全部 Blender 表现。
