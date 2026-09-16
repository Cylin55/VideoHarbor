@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo 正在建立 Python 環境...
    python -m venv .venv
    if errorlevel 1 (
        echo 找不到 Python，請先安裝 Python 3.11 或更新版本。
        pause
        exit /b 1
    )
)
echo 正在檢查必要套件...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
start "VideoHarbor" ".venv\Scripts\pythonw.exe" main.py
