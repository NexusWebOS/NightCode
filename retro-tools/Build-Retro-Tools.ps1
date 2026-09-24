$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name DiskDude --icon assets/disk-dude.ico --add-data 'assets;assets' --add-data 'burn-data-disc.ps1;.' disk_dude.py
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name Netcon --icon assets/netcon.ico --add-data 'assets;assets' netcon.py
Write-Host 'Built dist\DiskDude.exe and dist\Netcon.exe'
