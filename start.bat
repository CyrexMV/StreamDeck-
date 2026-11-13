@echo off
chcp 65001 >nul
title TabDeck
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)

if not exist ".venv\Scripts\python.exe" (
  echo Erster Start: richte Python-Umgebung ein ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo.
    echo Python wurde nicht gefunden. Bitte Python 3.10 oder neuer installieren:
    echo https://www.python.org/downloads/  ^(Haken bei "Add python.exe to PATH" setzen^)
    pause
    exit /b 1
  )
)

echo Pruefe Abhaengigkeiten ...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo Installation der Abhaengigkeiten fehlgeschlagen. Besteht eine Internetverbindung?
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements-windows.txt
if errorlevel 1 (
  echo.
  echo Hinweis: Einige optionale Windows-Pakete liessen sich nicht installieren.
  echo TabDeck startet trotzdem - nur Lautstaerke pro Programm bzw. "Laeuft gerade" fehlen evtl.
  echo.
)

".venv\Scripts\python.exe" -m server --open %*
pause
