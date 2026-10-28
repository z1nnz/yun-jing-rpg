# Runs the terrain acceptance checks (or the FBX model inventory) in the pinned Unity Editor.
# The scene named in the config must already be generated, e.g. ./tools/unity.ps1 -Target WorldPreview.
#   ./tools/qingxi-terrain/check-grounding.ps1                                  # default config
#   ./tools/qingxi-terrain/check-grounding.ps1 -Config tools/qingxi-terrain/checks/<name>.json
#   ./tools/qingxi-terrain/check-grounding.ps1 -Inventory                       # writes unity-models.json
param(
    [string]$Config = 'tools/qingxi-terrain/checks/qingxi-world-preview.json',
    [switch]$Inventory,
    [string]$EditorPath = 'D:\DevTools\Unity\6000.0.82f1\Editor\Unity.exe'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$gamePath = Join-Path $projectRoot 'apps/game'
if (-not (Test-Path -LiteralPath $EditorPath)) { throw "Unity not found: $EditorPath" }
New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'artifacts/terrain-check') | Out-Null
$name = if ($Inventory) { 'unity-models' } else { [IO.Path]::GetFileNameWithoutExtension($Config) }
$log = Join-Path $projectRoot "artifacts/terrain-check/unity-$name.log"
$method = if ($Inventory) { 'YunJing.Editor.QingxiGroundingCheck.InventoryModels' } else { 'YunJing.Editor.QingxiGroundingCheck.Run' }
$arguments = @('-batchmode','-nographics','-projectPath','.','-executeMethod',$method,'-logFile',('"' + $log + '"'))
if (-not $Inventory) { $arguments += @('-groundingConfig', ('"' + (Resolve-Path (Join-Path $projectRoot $Config)) + '"')) }
$process = Start-Process -FilePath $EditorPath -WorkingDirectory $gamePath -ArgumentList $arguments -WindowStyle Hidden -PassThru
$process.WaitForExit()
$process.Refresh()
if (-not $Inventory) {
    $report = Join-Path $projectRoot "artifacts/terrain-check/$name.md"
    if (Test-Path $report) { Get-Content -LiteralPath $report -Encoding utf8 }
}
if ($process.ExitCode -ne 0) { Get-Content -LiteralPath $log -Tail 20; throw "Terrain check failed ($($process.ExitCode)). Log: $log" }
Write-Host "Done. Log: $log"
