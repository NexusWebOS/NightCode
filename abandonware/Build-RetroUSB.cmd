@echo off
REM Retro USB: fills a USB stick with DOSBox, free DOS classics and strategy guides.
REM Extra options: Build-RetroUSB.cmd --list   (see python -m retrousb --help)
cd /d "%~dp0"
where py >nul 2>nul && (py -3 -m retrousb %* & goto done)
where python >nul 2>nul && (python -m retrousb %* & goto done)
echo Python 3.8 or newer is needed: https://www.python.org/downloads/
:done
pause
