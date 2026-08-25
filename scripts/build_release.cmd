@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set "APP_DIR=%ROOT%\src\ClassTool"
set "DOWNLOAD_DIR=%ROOT%\download"
set "ICON_PATH=%ROOT%\assets\logo.ico"

cd /d "%APP_DIR%" || exit /b 1

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name ClassTool ^
  --icon "%ICON_PATH%" ^
  --add-data "%APP_DIR%\language;language" ^
  --hidden-import PySide6.QtMultimedia ^
  --hidden-import PySide6.QtMultimediaWidgets ^
  main.py

if errorlevel 1 exit /b 1

if not exist "%DOWNLOAD_DIR%" mkdir "%DOWNLOAD_DIR%"
if not exist "%DOWNLOAD_DIR%\tools" mkdir "%DOWNLOAD_DIR%\tools"
if not exist "%DOWNLOAD_DIR%\data" mkdir "%DOWNLOAD_DIR%\data"

copy /y "%APP_DIR%\dist\ClassTool.exe" "%DOWNLOAD_DIR%\ClassTool.exe" >nul
copy /y "%APP_DIR%\tools\calculator_tool.py" "%DOWNLOAD_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\countdown_timer.py" "%DOWNLOAD_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\document_camera_tool.py" "%DOWNLOAD_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\random_picker.py" "%DOWNLOAD_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\screen_doodle_tool.py" "%DOWNLOAD_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\voting_tool.py" "%DOWNLOAD_DIR%\tools\" >nul
if not exist "%DOWNLOAD_DIR%\data\tools_data.json" echo {}>"%DOWNLOAD_DIR%\data\tools_data.json"

rmdir /s /q "%APP_DIR%\build" 2>nul
rmdir /s /q "%APP_DIR%\dist" 2>nul
del /q "%APP_DIR%\ClassTool.spec" 2>nul

echo.
echo Build complete:
echo %DOWNLOAD_DIR%

endlocal
