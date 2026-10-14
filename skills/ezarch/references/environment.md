# 按需准备工具环境

已有环境或现有脚本能够完成任务时，可以直接使用。纯 SVG 文本生成不需要安装 EZarch、CadQuery 或 Blender。下面是选择随库工具时的安装方法，不是每次任务的前置步骤。

## 随库环境

从 SKILL.md 所在目录确定 `<skill>`。安装器使用 uv、Python 3.12 和锁文件，在 skill 内建立 `.venv`，不替换系统 Python。

```sh
# macOS；路径含空格时保留引号
sh "<skill>/scripts/bootstrap.sh" --profile core
"<skill>/.venv/bin/python" "<skill>/scripts/run.py" doctor
```

```powershell
# Windows
powershell -File "<skill>/scripts/bootstrap.ps1" -Profile core
& "<skill>/.venv/Scripts/python.exe" "<skill>/scripts/run.py" doctor
```

| 安装配置 | 实际准备的能力 |
|---|---|
| core | 参考读取、独立二维 Drawing、SVG/PDF、排版、分析与检查助手 |
| model / draft | core + CadQuery/OCCT、网格与交换库；draft 是模型投影命令的安装别名 |
| render | core + 检测或安装 Blender；不自动安装 CadQuery |
| all | 建模与渲染依赖 |
| dev | Python 开发和测试依赖；用于维护仓库 |

配置增量安装。首次准备依赖需要网络；已有兼容 Blender 会被复用，否则下载官方 4.5 LTS 并校验。受支持的平台为 Windows x64、macOS x64/arm64；实际测试状态见仓库实施记录。安装器会准备随库仿宋字体，但选用其他工具或字体不依赖该字体。

随库建模环境使用 CadQuery 2.8 / OCP 7.9.3 / VTK 9.6.2；包含的 rhino3dm 安装包要求 macOS 14+。依赖锁为 Intel Mac 保留可用的 Numba/llvmlite 安装包，uv 对指定原生依赖使用 wheel，避免在用户电脑临时编译。已有其他可用环境仍可按任务使用。

`scripts/run.py` 只是启动 skill 私有 `.venv` 的便捷入口。其他兼容环境也可以安装 Python 包后运行 `python -m ezarch.cli`，或直接导入需要的 API。`doctor` 返回环境状态，适合缺命令、版本或后端不确定时使用。

## 操作入口

`<python> <skill>/scripts/run.py --help` 列出独立命令；每个命令有自己的输入，不存在必须依次执行的总流程。例如：

```text
reference <PDF|image> --out <dir>
views <project.yml> --only <view-id> --formats dxf pdf --out <dir>
render <scene.json|blend|glb> --camera <id|all> --out <dir>
board <board.yml> --formats pdf --out <dir>
```

各命令会在所选输出目录写执行记录，这是封装的副产物，不要求用户把它列入交付。真实项目、下载素材和生成文件使用项目目录；安装目录保存工具。
