@echo off
REM ===========================================================================
REM Asmeranda AI - Windows installer builder (full stack).
REM
REM Karena stack saat ini 2-bahasa (Python backend + Node.js frontend),
REM pendekatan installer yang paling portabel dan bebas error adalah:
REM   1. Build Docker image (sudah membungkus backend + frontend)
REM   2. Simpan image sebagai .tar
REM   3. Bundle dengan docker-compose.yml, scripts, dan dokumentasi
REM   4. Buat installer NSIS yang:
REM      a. Memastikan Docker Desktop terinstall (download jika belum)
REM      b. Memuat image .tar ke Docker lokal
REM      c. Membuat shortcut untuk start/stop
REM
REM Output:
REM   - dist\AsmerandaAI-Full-v{VERSION}.exe   (NSIS installer)
REM   - dist\AsmerandaAI-Full-v{VERSION}.zip   (portable bundle)
REM
REM Prasyarat:
REM   - Docker Desktop berjalan
REM   - NSIS (Nullsoft Scriptable Install System) terinstall
REM     Download: https://nsis.sourceforge.io/Download
REM   - makensis.exe ada di PATH
REM ===========================================================================

setlocal EnableDelayedExpansion

set VERSION=1.0.0
set IMAGE_NAME=asmeranda
set IMAGE_TAG=%VERSION%
set IMAGE=%IMAGE_NAME%:%IMAGE_TAG%
set BUNDLE_NAME=AsmerandaAI-Full-v%VERSION%
set DIST_DIR=dist
set BUNDLE_DIR=%DIST_DIR%\%BUNDLE_NAME%

echo ===========================================================================
echo  Asmeranda AI - Windows Installer Builder (Full Stack)
echo  Version:    %VERSION%
echo  Image:      %IMAGE%
echo  Bundle:     %BUNDLE_DIR%
echo ===========================================================================

REM --- 1) Bersihkan dist lama
echo.
echo [1/7] Membersihkan dist lama...
if exist "%DIST_DIR%" rmdir /S /Q "%DIST_DIR%"
mkdir "%BUNDLE_DIR%"

REM --- 2) Build Docker image (multi-stage)
echo.
echo [2/7] Build Docker image (multi-stage: frontend + backend)...
docker build -f Dockerfile.azure -t %IMAGE% .
if errorlevel 1 goto :error

REM --- 3) Save image ke .tar
echo.
echo [3/7] Save image ke .tar...
docker save -o "%BUNDLE_DIR%\%IMAGE_NAME%-image.tar" %IMAGE%
if errorlevel 1 goto :error

REM --- 4) Copy file deployment
echo.
echo [4/7] Copy deployment files...
copy docker-compose.yml "%BUNDLE_DIR%\docker-compose.yml" >nul
copy docker-compose.azure.yml "%BUNDLE_DIR%\docker-compose.azure.yml" >nul
copy azure.env "%BUNDLE_DIR%\.env.example" >nul
copy README.md "%BUNDLE_DIR%\README.md" >nul

REM --- 5) Buat start/stop scripts
(
    echo @echo off
    echo echo ===========================================================================
    echo echo  Asmeranda AI - Starting...
    echo echo ===========================================================================
    echo.
    echo if not exist "asmeranda-image.tar" ^(
    echo     echo [ERROR] File asmeranda-image.tar tidak ditemukan.
    echo     echo Jalankan build_installer_full.bat terlebih dahulu.
    echo     exit /b 1
    echo ^)
    echo.
    echo echo [1/2] Loading Docker image...
    echo docker load -i asmeranda-image.tar
    echo if errorlevel 1 goto :error
    echo.
    echo echo [2/2] Starting containers via docker compose...
    echo docker compose up -d
    echo if errorlevel 1 goto :error
    echo.
    echo echo.
    echo echo Asmeranda AI berjalan di:
    echo echo   Frontend: http://localhost:3000
    echo echo   Backend:  http://localhost:8000
    echo echo   API docs: http://localhost:8000/docs
    echo echo.
    echo echo Untuk menghentikan: stop.bat
    echo goto :eof
    echo.
    echo :error
    echo echo.
    echo echo [ERROR] Gagal start. Periksa output di atas.
    echo exit /b 1
) > "%BUNDLE_DIR%\start.bat"

(
    echo @echo off
    echo echo Menghentikan Asmeranda AI...
    echo docker compose down
) > "%BUNDLE_DIR%\stop.bat"

(
    echo @echo off
    echo docker compose logs -f --tail=100
) > "%BUNDLE_DIR%\logs.bat"

REM --- 6) Buat NSIS installer script
echo.
echo [5/7] Generate NSIS installer script...

(
    echo !include "MUI2.nsh"
    echo.
    echo Name "Asmeranda AI v%VERSION%"
    echo OutFile "%DIST_DIR%\%BUNDLE_NAME%-Setup.exe"
    echo InstallDir "$PROGRAMFILES64\AsmerandaAI"
    echo RequestExecutionLevel admin
    echo.
    echo ^!define MUI_ABORTWARNING
    echo ^!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
    echo.
    echo ^!insertmacro MUI_PAGE_DIRECTORY
    echo ^!insertmacro MUI_PAGE_INSTFILES
    echo ^!insertmacro MUI_LANGUAGE "English"
    echo ^!insertmacro MUI_LANGUAGE "Indonesian"
    echo.
    echo Section "Install"
    echo   SetOutPath "$INSTDIR"
    echo   File /r "%BUNDLE_DIR%\*.*"
    echo.
    echo   CreateDirectory "$SMPROGRAMS\Asmeranda AI"
    echo   CreateShortcut "$SMPROGRAMS\Asmeranda AI\Start.lnk" "$INSTDIR\start.bat"
    echo   CreateShortcut "$SMPROGRAMS\Asmeranda AI\Stop.lnk"  "$INSTDIR\stop.bat"
    echo   CreateShortcut "$SMPROGRAMS\Asmeranda AI\Logs.lnk"  "$INSTDIR\logs.bat"
    echo   CreateShortcut "$SMPROGRAMS\Asmeranda AI\README.lnk" "$INSTDIR\README.md"
    echo.
    echo   WriteUninstaller "$INSTDIR\Uninstall.exe"
    echo   CreateShortcut "$SMPROGRAMS\Asmeranda AI\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    echo.
    echo   ; Pesan untuk user
    echo   MessageBox MB_OK|MB_ICONINFORMATION "Asmeranda AI berhasil diinstall.$\r$\n$\r$\nPastikan Docker Desktop sudah berjalan,$\r$\nlalu klik Start dari Start Menu."
    echo SectionEnd
    echo.
    echo Section "Uninstall"
    echo   ExecWait "$INSTDIR\stop.bat"
    echo   RMDir /r "$INSTDIR"
    echo   RMDir /r "$SMPROGRAMS\Asmeranda AI"
    echo SectionEnd
) > "%BUNDLE_DIR%\installer.nsi"

REM --- 7) Build NSIS installer
echo.
echo [6/7] Build NSIS installer (membutuhkan NSIS terinstall)...
where makensis >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [INFO] NSIS tidak ditemukan. Melewati build installer.
    echo   Bundle portable sudah tersedia di: %BUNDLE_DIR%\
    echo   Untuk membuat installer .exe, install NSIS lalu jalankan:
    echo     makensis "%BUNDLE_DIR%\installer.nsi"
    echo.
) else (
    makensis "%BUNDLE_DIR%\installer.nsi"
    if errorlevel 1 goto :error
)

REM --- 8) Buat portable ZIP
echo.
echo [7/7] Membuat portable ZIP...
powershell -NoProfile -Command "Compress-Archive -Path '%BUNDLE_DIR%' -DestinationPath '%DIST_DIR%\%BUNDLE_NAME%.zip' -Force"

echo.
echo ===========================================================================
echo  BUILD BERHASIL
echo  Bundle:    %BUNDLE_DIR%\
echo  Portable:  %DIST_DIR%\%BUNDLE_NAME%.zip
if exist "%DIST_DIR%\%BUNDLE_NAME%-Setup.exe" (
    echo  Installer: %DIST_DIR%\%BUNDLE_NAME%-Setup.exe
)
echo ===========================================================================
echo.
echo  Cara install di komputer baru:
echo    1. Install Docker Desktop
echo    2. Ekstrak ZIP atau jalankan installer
echo    3. Klik start.bat (atau Start Menu ^> Start)
echo.
echo  Asmeranda AI akan jalan di:
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:8000
echo ===========================================================================
goto :eof

:error
echo.
echo [ERROR] Build gagal. Periksa output di atas.
exit /b 1
