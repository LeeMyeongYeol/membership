@echo off
setlocal ENABLEDELAYEDEXPANSION

rem ===========================================
rem  Movie Finder: Auto-start Backend & Frontend
rem ===========================================

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONT=%ROOT%fronthead"
set "VENV=%BACKEND%\.venv"

echo.
echo [Step 1] Checking folders...
if not exist "%BACKEND%" (
  echo Missing backend folder: "%BACKEND%"
  pause
  exit /b 1
)
if not exist "%FRONT%" (
  echo Missing fronthead folder: "%FRONT%"
  pause
  exit /b 1
)

echo.
echo [Step 2] Checking Python...
where python >nul 2>&1
if errorlevel 1 (
  echo Python not found in PATH.
  pause
  exit /b 1
)

echo.
echo [Step 3] Creating virtual environment (if needed)...
if not exist "%VENV%\Scripts\python.exe" (
  pushd "%BACKEND%"
  python -m venv .venv
  if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
  )
  popd
) else (
  echo Virtual environment already exists.
)

echo.
echo [Step 4] Installing backend dependencies...
pushd "%BACKEND%"
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip >nul
"%VENV%\Scripts\python.exe" -m pip install fastapi "uvicorn[standard]" httpx python-dotenv >nul
popd

echo.
echo [Step 5] Preparing .env file...
if not exist "%BACKEND%\.env" (
  echo TMDB_API_KEY=ddd654eb8622a67e04f93f613653426d> "%BACKEND%\.env"
  echo OMDB_API_KEY=f1b92691>> "%BACKEND%\.env"
  echo Created .env file.
) else (
  echo Using existing .env file.
)

echo.
echo [Step 6] Starting servers...

rem ---- Start Backend (FastAPI / Uvicorn) ----
start "MovieFinder Backend" cmd /k ^
 "cd /d ""%BACKEND%"" && ""%VENV%\Scripts\python.exe"" -m uvicorn app:app --reload --port 8000"

rem ---- Wait a few seconds ----
timeout /t 3 /nobreak >nul

rem ---- Start Frontend (HTTP server) ----
start "MovieFinder Frontend" cmd /k ^
 "cd /d ""%FRONT%"" && python -m http.server 5173"

rem ---- Open in default browser ----
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5173"

echo.
echo ==============================================
echo  ✅ Backend: http://127.0.0.1:8000
echo  ✅ Frontend: http://127.0.0.1:5173
echo ==============================================
echo.
exit /b 0
