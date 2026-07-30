@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set "APP_DIR=%ROOT%\src\ClassTool"
set "RELEASE_DIR=%ROOT%\release\ClassTool_pack"
set "ICON_PATH=%ROOT%\assets\logo.ico"

cd /d "%APP_DIR%" || exit /b 1

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name ClassTool ^
  --icon "%ICON_PATH%" ^
  --hidden-import PySide6.QtMultimedia ^
  --hidden-import PySide6.QtMultimediaWidgets ^
  main.py

if errorlevel 1 exit /b 1

if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%\tools"
mkdir "%RELEASE_DIR%\data"

copy /y "%APP_DIR%\dist\ClassTool.exe" "%RELEASE_DIR%\ClassTool.exe" >nul
copy /y "%APP_DIR%\tools\calculator_tool.py" "%RELEASE_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\countdown_timer.py" "%RELEASE_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\document_camera_tool.py" "%RELEASE_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\random_picker.py" "%RELEASE_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\screen_doodle_tool.py" "%RELEASE_DIR%\tools\" >nul
echo {}>"%RELEASE_DIR%\data\tools_data.json"

rmdir /s /q "%APP_DIR%\build" 2>nul
rmdir /s /q "%APP_DIR%\dist" 2>nul
del /q "%APP_DIR%\ClassTool.spec" 2>nul

echo.
echo Build complete:
echo %RELEASE_DIR%

endlocal
