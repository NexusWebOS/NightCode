$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3 -m PyInstaller --noconfirm --onedir --windowed --name NightCode nightcode.py
Write-Host 'Built dist\NightCode\NightCode.exe'
