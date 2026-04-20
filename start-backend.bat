@echo off
cd /d "%~dp0backend"
echo Starting SafeCodeAI backend on port 8000...
..\venv\Scripts\activate.bat 2>nul || ..\.venv\Scripts\activate.bat 2>nul || echo Virtual env not found. Make sure you set it up.
set DATABASE_URL=sqlite:///./safecodeai.db
uvicorn main:app --reload --reload-dir . --reload-dir ../src --port 8000
