@echo off
echo ===================================================
echo  Starting CampusMind Agent (React)
echo ===================================================
echo.
echo 1. Starting FastAPI backend on http://127.0.0.1:8000 ...
start "FastAPI Backend" cmd /k "python -m uvicorn src.ui.server:app --host 127.0.0.1 --port 8000 --reload"

echo 2. Starting Vite React server on http://localhost:5173 ...
cd frontend
start "React Vite App" cmd /k "npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo ===================================================
echo  Both services launched!
echo  Open your browser at: http://localhost:5173
echo ===================================================
timeout /t 3 /nobreak >nul
start http://localhost:5173
