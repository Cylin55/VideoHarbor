$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
& ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name "VideoHarbor" --collect-all yt_dlp main.py
# 某些開發環境的 PATH 含有 Poppler，PyInstaller 可能誤收其 ICU DLL。
# Qt on Windows 應使用系統 ICU；誤收版本會讓 QtCore 無法載入。
$internalPath = Join-Path $PSScriptRoot "dist\VideoHarbor\_internal"
Remove-Item -LiteralPath (Join-Path $internalPath "icuuc.dll") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $internalPath "icudt78.dll") -Force -ErrorAction SilentlyContinue
Write-Host "完成：dist\VideoHarbor\VideoHarbor.exe"
