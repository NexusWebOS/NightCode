$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3 -m PyInstaller --noconfirm --onedir --windowed --name NightCode --add-data 'assets/nightcode-marquee-gpt-v2.png;assets' nightcode.py
Write-Host 'Built dist\NightCode\NightCode.exe'
