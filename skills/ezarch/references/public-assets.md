# 公开三维素材

不随 skill 放模型/贴图库，不依赖个人素材目录，不固定家具清单。AI 按每次设计检索公开可读可下载素材；下载是项目依赖。

## 官方入口（2026-10-13 核查）

| 来源 | 用途 | 路径 |
|---|---|---|
| Poly Haven | HDRI、PBR、部分模型 | https://polyhaven.com/our-api 、https://api.polyhaven.com/ 、https://docs.polyhaven.com/en/faq |
| ambientCG | 建筑材质 | https://docs.ambientcg.com/api/ 、https://docs.ambientcg.com/license/ |
| Blendkit（原 BlenderKit，可选） | 额外家具和软装 | https://www.blendkit.com/docs/licenses/ 、https://github.com/BlenderKit/bk_client |

Poly Haven 素材 CC0；在线 API 当前免费，要求唯一 User-Agent 和清楚的来源标识。素材许可与服务条款分别处理。ambientCG 素材 CC0，读取当时 API 文档。Blendkit 逐资源区分 CC0/Royalty Free；需登录/付费或限制分发的资源不纳入无账号默认路线。

## 项目获取方法

1. 从设计确定类别、外形、实际尺寸、风格、镜头距离。主体和定制构件仍自行设计。
2. 读元数据、看预览再选择。Poly Haven `GET /assets?t=models|textures|hdris` 检索；`GET /files/<id>` 返回文件 URL、hash、大小及依赖。使用唯一 User-Agent，例如 `EZarch/0.2`；不猜 CDN 路径。
3. 只获取需要的分辨率/格式和贴图到项目 dependencies/；复用已存在文件，不全库同步。检查 hash、许可、格式和失效链接。
4. 写 assets.json：ID、原页面、下载 URL、许可、日期、hash、单位/朝向、实际尺寸和用途。不执行下载包脚本，Blender 禁止自动运行脚本。
5. 导入后检查 UV、色彩空间、法线、尺寸、底部位置和朝向。家具不非等比压扁适配；图块 footprint 对齐。导入后的真实包围盒还要按旋转/缩放计算占地，检查植被、散布和家具是否穿墙、穿地或进入通行区；素材原点在室外不代表全部几何在室外。预览不合格则修正或更换。
6. 打包实际依赖或 pack 到 BLEND，重开验证；按许可决定哪些源文件能公开。

Material.maps 可接 base_color/roughness/normal/metallic，相对项目路径；texture_size_m 控制实际重复尺度。render.hdri 接下载 HDRI；render.asset_instances 接 GLB/GLTF/BLEND（见 project-data）。这不是 skill 附带素材库。

无合适公开资源可按设计程序化制作，不能用低质占位对象冒充最终精细资产。资源下载成功和实际视觉质量分别验收。

内置按需下载入口：把选择写为 `asset.yml`，例如 `provider: polyhaven`、
`id: dining_chair_02`、`kind: model`、`resolution: 1k`，执行：

```sh
python scripts/run.py asset /project/asset.yml --out /project/dependencies/chair
```

`kind` 支持 model、texture、hdri。客户端读取官方 `/files/{id}`，下载 GLTF
及全部贴图/缓冲区依赖，校验提供方 MD5 并保存 SHA256 来源清单。
模型尺寸必须在导入后测量，不能从文件名猜测。材质入口获取 Diffuse/Rough/nor_gl
三个贴图；缺少字段的素材应换源或写项目适配器，不能悄悄跳过。
Blender 以集合实例复用重复家具和树木，保存时打包贴图。场景指纹包含 GLTF
引用的本地纹理和缓冲区，修改它们会使旧成果过期。

可用 `oriented_footprint(size_mm, position_mm, rotation_z_deg)` 取得导入后实测外廓（size_mm 已乘均匀比例）的旋转占地，再用 `check_clearances` 与室内禁入区/通道检查。此矩形包围盒是保守检查，复杂形状可换精确轮廓。

景观检查还须覆盖入口、步道、坡道与铺装。地被不得越入这些通路；树冠可以跨越的空间应按净高与树干位置另判，不能对所有植物套用同一禁入盒。效果图应从鸟瞰和人视两种角度复核，发现问题后同步保留布局修正来源。
