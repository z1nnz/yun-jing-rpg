param(
    [ValidateSet('Generate','Windows','Android','LinuxServer')] [string]$Target = 'Generate',
    [string]$EditorPath = 'C:\Program Files\Unity\Hub\Editor\6000.0.85f1\Editor\Unity.exe'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$gamePath = Join-Path $projectRoot 'apps/game'
if (-not (Test-Path -LiteralPath $EditorPath)) { throw "Unity not found: $EditorPath" }
$methods = @{ Generate='Generate'; Windows='BuildWindows'; Android='BuildAndroid'; LinuxServer='BuildLinuxServer' }
New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'artifacts') | Out-Null
$log = Join-Path $projectRoot "artifacts/unity-$Target.log"
$method = 'YunJing.Editor.ProjectBuilder.' + $methods[$Target]
$arguments = @('-batchmode','-nographics','-quit','-projectPath','.', '-executeMethod',$method,'-logFile',('"' + $log + '"'))
$process = Start-Process -FilePath $EditorPath -WorkingDirectory $gamePath -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) { Get-Content -LiteralPath $log -Tail 35; throw "Unity failed ($($process.ExitCode)). Log: $log" }
Write-Host "Unity $Target completed. Log: $log"
