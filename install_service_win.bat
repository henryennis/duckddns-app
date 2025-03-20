@echo off
setlocal enabledelayedexpansion

echo Duck DNS Updater Service Installer for Windows
echo =============================================

REM Get the directory where the script is located
set "SCRIPT_DIR=%~dp0"

REM Set the path to the Python executable and main script
set "PYTHON_PATH=pythonw.exe"
set "SCRIPT_PATH=%SCRIPT_DIR%duckdns_updater.py"

if "%1"=="--install" goto :install
if "%1"=="--uninstall" goto :uninstall

echo.
echo Usage:
echo   install_service_win.bat --install   : Install Duck DNS Updater as a startup service
echo   install_service_win.bat --uninstall : Remove Duck DNS Updater from startup
goto :eof

:install
echo.
echo Installing Duck DNS Updater as a startup service...

REM Create a shortcut in the startup folder
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\DuckDNSUpdater.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%SHORTCUT_PATH%"
echo sLinkFile = "%STARTUP_FOLDER%\DuckDNSUpdater.lnk" >> "%SHORTCUT_PATH%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%SHORTCUT_PATH%"
echo oLink.TargetPath = "%PYTHON_PATH%" >> "%SHORTCUT_PATH%"
echo oLink.Arguments = "%SCRIPT_PATH%" >> "%SHORTCUT_PATH%"
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> "%SHORTCUT_PATH%"
echo oLink.Description = "Duck DNS Updater" >> "%SHORTCUT_PATH%"
echo oLink.IconLocation = "%PYTHON_PATH%, 0" >> "%SHORTCUT_PATH%"
echo oLink.WindowStyle = 7 >> "%SHORTCUT_PATH%"
echo oLink.Save >> "%SHORTCUT_PATH%"

REM Execute the VBS script to create the shortcut
cscript //nologo "%SHORTCUT_PATH%"
del "%SHORTCUT_PATH%"

REM Create scheduled task for auto-restart on logon
schtasks /create /tn "DuckDNSUpdater" /tr "'%PYTHON_PATH%' '%SCRIPT_PATH%'" /sc onlogon /rl highest /f

echo Duck DNS Updater has been installed to run on startup.
echo.
goto :eof

:uninstall
echo.
echo Uninstalling Duck DNS Updater service...

REM Remove the shortcut from startup folder
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DuckDNSUpdater.lnk" (
    del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DuckDNSUpdater.lnk"
)

REM Remove the scheduled task
schtasks /delete /tn "DuckDNSUpdater" /f 2>nul

echo Duck DNS Updater has been removed from startup.
echo.
goto :eof