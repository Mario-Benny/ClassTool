@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set "APP_DIR=%ROOT%\src\ClassTool"
set "RELEASE_DIR=%ROOT%\release"
set "ICON_PATH=%ROOT%\assets\logo.ico"

for /f "tokens=3" %%V in ('findstr /B /C:"APP_VERSION =" "%APP_DIR%\toolkit\core\app_info.py"') do set "VERSION=%%~V"
set "VERSION=%VERSION:"=%"
set "PACKAGE_NAME=ClassTool-v%VERSION%-win-x64"
set "PACKAGE_DIR=%RELEASE_DIR%\%PACKAGE_NAME%"
set "ZIP_PATH=%RELEASE_DIR%\%PACKAGE_NAME%.zip"
set "CHECKSUM_PATH=%RELEASE_DIR%\%PACKAGE_NAME%.zip.sha256"

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

if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
mkdir "%PACKAGE_DIR%\tools"
mkdir "%PACKAGE_DIR%\data"

copy /y "%APP_DIR%\dist\ClassTool.exe" "%PACKAGE_DIR%\ClassTool.exe" >nul
rem Keep the source-only plugin template out of release packages, including old leftovers.
copy /y "%APP_DIR%\tools\calculator_tool.py" "%PACKAGE_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\countdown_timer.py" "%PACKAGE_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\document_camera_tool.py" "%PACKAGE_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\random_picker.py" "%PACKAGE_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\screen_doodle_tool.py" "%PACKAGE_DIR%\tools\" >nul
copy /y "%APP_DIR%\tools\voting_tool.py" "%PACKAGE_DIR%\tools\" >nul
echo {}>"%PACKAGE_DIR%\data\tools_data.json"

python -c "from pathlib import Path; from zipfile import ZIP_DEFLATED, ZipFile; root=Path(r'%PACKAGE_DIR%'); archive=Path(r'%ZIP_PATH%'); files=[path for path in root.rglob('*') if path.is_file()]; bundle=ZipFile(archive, 'w', ZIP_DEFLATED); [bundle.write(path, path.relative_to(root.parent)) for path in files]; bundle.close()"
if errorlevel 1 exit /b 1
python -c "from pathlib import Path; import hashlib; archive=Path(r'%ZIP_PATH%'); stream=archive.open('rb'); digest=hashlib.file_digest(stream, 'sha256').hexdigest().upper(); stream.close(); Path(r'%CHECKSUM_PATH%').write_text(digest + '  %PACKAGE_NAME%.zip\n', encoding='ascii')"
if errorlevel 1 exit /b 1

rmdir /s /q "%APP_DIR%\build" 2>nul
rmdir /s /q "%APP_DIR%\dist" 2>nul
del /q "%APP_DIR%\ClassTool.spec" 2>nul

echo.
echo Build complete:
echo %ZIP_PATH%
echo %CHECKSUM_PATH%

endlocal
