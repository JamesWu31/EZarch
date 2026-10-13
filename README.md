# EZarch

**面向 AI 的模块化建筑出图 skill。** 从需求、参考图或已有模型出发，用程序生成建筑模型、平立剖、分析图、渲染和图板。你选择需要的模块；代理负责环境准备、中间转换、执行、检查与交付。不会默认跑完整设计流程。

第一期采用开放工具，支持 **macOS（Intel / Apple Silicon）与 Windows x64**。Rhino、SketchUp、AutoCAD 的原生程序化控制，以及 IFC，列入后续阶段。

## 能做什么

| 选用模块 | 输入与工作方式 | 主要交付 |
|---|---|---|
| 需求 / 参考 | AI 识别空间约束、PDF 矢量与页面、图像标定；明确已知与推测 | 设计数据、面积表、参考证据 |
| 精确建模 | CadQuery / OCCT 实体；墙、洞口、板、楼梯、布尔切割；项目脚本可扩展曲面 | STEP、命名构件、共享场景 |
| 二维 / 模型出图 | 模型真实剖切 + 隐藏线投影；或代理使用 ezdxf 作独立二维图 | 毫米 1:1 DXF、定比例矢量 PDF、SVG |
| 二三维联动 | 带单位的 DXF 闭合边界拉伸；外部 STEP 实体生成视图 | 可追溯的模型 / 平立剖 |
| 渲染 | Blender Python / Cycles，模型导入、程序材质、相机、日光、CPU/GPU 检测 | PNG、可复现场景 BLEND |
| 分析图 | 从空间多边形生成面积、功能、流线、虚实；可编写项目级 SVG | 可编辑 SVG、矢量 PDF |
| 图板 | 独立 YAML 模板组合外部 PDF 与图片；保留图纸比例、检查分辨率及重叠 | 多页 PDF、SVG、预览 PNG |
| 交换 / 审计 | 回读单位、尺寸、数量、实体有效性、图纸比例与输入版本 | 编辑文件、数值审计、视觉复核记录 |

几何和设计判断由 AI 根据具体任务完成。现有构件库不是全功能建筑软件；异形建筑应使用同一环境中的 CadQuery / Blender API 编写项目脚本。图像不能唯一确定不可见尺寸，示意分析也不等于结构或环境性能模拟。

## 文件兼容

- **AutoCAD：DXF**，保留图层、文字、填充、尺寸实体。
- **Rhino：3DM + STEP**。3DM 是有名称和材质的可编辑网格；STEP 保存精确实体，两者一起交付。
- **SketchUp：COLLADA DAE 1.4.1**，带单位和构件节点。
- 通用：GLB、PDF、SVG、PNG、BLEND。

不需要安装三个商业软件来生成上述交换文件。本期不提供原生 DWG/SKP 写入，也不把开放库回读等同于商业软件内的验收。目标软件版本可能影响导入后的分组、字体和材质表现。

## 安装为 skill

可安装内容全部位于 **`skills/ezarch`**；复制或通过 skill 安装器安装这一整个目录，不要只复制 `SKILL.md`。安装后的代理读取 [入口](skills/ezarch/SKILL.md)，按模块执行。示例请求：

> 用 $ezarch 根据这份需求设计一个庭院住宅，先只做平面和精确模型。
>
> 用 $ezarch 给这个模型做两张渲染；沿用现有设计。
>
> 用 $ezarch 将这些 PDF 和效果图放入两张 A1 图板，平面保持 1:100。

首次运行需要网络以下载 Python / 依赖；已安装的兼容 Blender 会被复用。否则渲染模块下载校验过的官方 Blender 4.5 LTS 到 skill 私有目录。安装器不捆绑商业软件，不修改系统 Python，不自动关闭系统安全检查。

开发者也可手动运行：

```sh
# macOS，仓库根目录
sh skills/ezarch/scripts/bootstrap.sh --profile all
skills/ezarch/.venv/bin/python skills/ezarch/scripts/run.py doctor
```

```powershell
# Windows，仓库根目录
powershell -File skills/ezarch/scripts/bootstrap.ps1 -Profile all
skills/ezarch/.venv/Scripts/python.exe skills/ezarch/scripts/run.py doctor
```

可选安装配置：`core`（参考、分析、排版）、`model` / `draft`（增加精确几何）、`render`（增加 Blender）、`all`、`dev`。配置增量安装，后选基础模块不会移除已经准备的建模能力。具体命令由代理完成，普通使用者无需自行处理每一步。

## 数据与精度

设计数据统一为毫米；DXF 模型空间 1:1；GLB 和 Blender 边界转换为米。PDF 按物理毫米出图，图板中的定比例图不自动缩放。每次运行记录输入和输出；源数据变更后审计可识别过期图纸与渲染。

默认网格化容差为 1 mm，曲线出图采样目标为 0.5 mm；这与 STEP 实体精度、源图的测量可信度是不同概念。毫米级坐标不代表施工级完整度。方案设计之外的节点、构造、规范与结构验算，需要相应设计输入和独立校核。

附带可自由分发的 **Fandol 仿宋衍生字体 EZarch Fang**；PDF/SVG 嵌入字体。它不是微软专有仿宋。CAD 文件需解析对应 TTF；安装器和交付包会提供同一字体。

## 验证与开发

[实施记录](docs/IMPLEMENTATION.md) 区分实测结果和待验证平台。[当前方案](docs/architecture-skill-design.md) 说明第一期范围；[后续原生适配](docs/native-roadmap.md) 保留第二期设计。

```sh
sh skills/ezarch/scripts/bootstrap.sh --profile dev
skills/ezarch/.venv/bin/python -m pytest -q tests
skills/ezarch/.venv/bin/ruff check --config ruff.toml skills/ezarch/src skills/ezarch/scripts tests tools
skills/ezarch/.venv/bin/python tools/package_skill.py --out ../EZarch-dist
```

CI 仅配置 Windows 和 macOS。真实建筑验证项目、参考照片、生成模型、渲染和图板均在独立目录，**不进入本仓库**。仓库中的测试只使用最小合成几何。

## License

EZarch 代码为 **AGPL-3.0-or-later**，见 [LICENSE](LICENSE)。字体及第三方依赖保留各自许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。本仓库不含付费素材、商业 CAD 安装包或 ArchDaily 原图。
