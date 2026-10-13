param([string]$Profile = "core", [switch]$InstallBlender)
$ErrorActionPreference = "Stop"
$EZarchSkillRoot = Split-Path $PSScriptRoot -Parent
$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCommand) {
    $EZarchUv = $uvCommand.Source
} else {
    $EZarchToolDir = Join-Path $EZarchSkillRoot ".ezarch/tools"
    New-Item -ItemType Directory -Force -Path $EZarchToolDir | Out-Null
    $installer = Join-Path $EZarchToolDir "install-uv.ps1"
    Invoke-WebRequest "https://astral.sh/uv/0.11.26/install.ps1" -OutFile $installer
    $oldDir = $env:UV_INSTALL_DIR
    $oldModify = $env:UV_NO_MODIFY_PATH
    try {
        $env:UV_INSTALL_DIR = $EZarchToolDir
        $env:UV_NO_MODIFY_PATH = "1"
        & $installer
    } finally {
        $env:UV_INSTALL_DIR = $oldDir
        $env:UV_NO_MODIFY_PATH = $oldModify
    }
    $EZarchUv = Join-Path $EZarchToolDir "uv.exe"
}
$arguments = @("run", "--no-project", "--python", "3.12", "python",
               (Join-Path $PSScriptRoot "bootstrap.py"), "--profile", $Profile)
if ($InstallBlender) { $arguments += "--install-blender" }
& $EZarchUv @arguments
exit $LASTEXITCODE
