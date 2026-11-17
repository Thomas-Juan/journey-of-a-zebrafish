@echo off
rem Builds JourneyOfAZebrafish.exe next to this file (needs Python 3.10+).
rem Temporary build files go to %TEMP% so OneDrive does not lock them.
cd /d "%~dp0"
python -m pip install --user pygame-ce numpy pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name JourneyOfAZebrafish --exclude-module tkinter --exclude-module PIL ^
  --icon "%~dp0game\icon.ico" --paths "%~dp0game" --distpath "%~dp0." ^
  --workpath "%TEMP%\zfbuild" --specpath "%TEMP%\zfbuild" "%~dp0game\main.py"
pause
