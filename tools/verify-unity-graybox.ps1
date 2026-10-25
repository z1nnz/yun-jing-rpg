param(
    [string]$EditorPath = 'D:\DevTools\Unity\6000.0.82f1\Editor\Unity.exe'
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $EditorPath)) { throw "Unity not found: $EditorPath" }
$root = Split-Path -Parent $PSScriptRoot
$project = Join-Path $root 'apps/game'
$artifacts = Join-Path $root 'artifacts'
New-Item -ItemType Directory -Force -Path $artifacts | Out-Null
$log = Join-Path $artifacts ('unity-graybox-' + [guid]::NewGuid().ToString('N') + '.log')
$arguments = @('-batchmode', '-nographics', '-quit', '-projectPath', ('"' + $project + '"'),
    '-executeMethod', 'YunJing.Editor.QingxiHuntStandaloneBuilder.Verify', '-logFile', ('"' + $log + '"'))
$process = Start-Process -FilePath $EditorPath -ArgumentList $arguments -WindowStyle Hidden -PassThru
if (-not $process.WaitForExit(900000)) {
    Stop-Process -Id $process.Id
    throw "Unity validation timed out. Log: $log"
}
$process.Refresh()
if ($process.ExitCode -ne 0 -or -not (Select-String -LiteralPath $log -SimpleMatch 'GRAYBOX_VERIFY_PASS:' -Quiet)) {
    throw "Unity graybox validation failed (exit $($process.ExitCode)). Log: $log"
}
Write-Output "Unity graybox generation and reload checks passed. Log: $log"

