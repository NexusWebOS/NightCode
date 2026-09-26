$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$assetArgs = @()
foreach ($asset in (Get-ChildItem -LiteralPath 'assets' -File -Filter '*.png')) {
    $assetArgs += '--add-data'
    $assetArgs += "assets/$($asset.Name);assets"
}
$assetArgs += @('--add-data', 'assets/spritecook/disk-dude-button-frame.png;assets/spritecook')
$assetArgs += @('--add-data', 'assets/spritecook/netcon-button-frame.png;assets/spritecook')
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name DiskDude --icon assets/disk-dude.ico @assetArgs --add-data 'burn-data-disc.ps1;.' disk_dude.py
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name Netcon --icon assets/netcon.ico @assetArgs netcon.py
Write-Host 'Built dist\DiskDude.exe and dist\Netcon.exe'
