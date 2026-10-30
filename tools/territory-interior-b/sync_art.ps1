# 把展示需要的模型與貼圖從版本庫內的交付位置複製進 Unity 專案（Assets/Art）。
# 只複製檔案本體；.meta 已在版本庫內，GUID 不會變。在 tools/territory-interior-b 下執行：
#   powershell -ExecutionPolicy Bypass -File sync_art.ps1
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$art = Join-Path $PSScriptRoot 'Assets\Art'

$exports = Join-Path $root 'art\exports\territory-interior-b'
foreach ($dir in Get-ChildItem $exports -Directory) {
    $dst = Join-Path $art ('TI18\' + $dir.Name)
    New-Item -ItemType Directory -Force $dst | Out-Null
    Copy-Item (Join-Path $dir.FullName ($dir.Name + '_v001.fbx')) $dst
    Copy-Item (Join-Path $dir.FullName 'model_info.json') $dst
    Copy-Item (Join-Path $dir.FullName 'Textures\*.png') $dst
}

$dondon = Join-Path $root 'art\incoming\dondon'
$existing = @(
    'DiscipleBed\v001\DiscipleBed_v001.fbx',
    'StorageChest\v001\StorageChest_v001.fbx',
    'MeditationCushion\v001\MeditationCushion_v001.fbx',
    'QPillBottle\v002\QPillBottle_v002.fbx',
    'SpiritHerbMature\v001\SpiritHerbMature_v001.fbx'
)
foreach ($p in $existing) { Copy-Item (Join-Path $dondon $p) (Join-Path $art 'Existing') }
Write-Host '完成：Assets/Art 已更新'
