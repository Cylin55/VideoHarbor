# VideoHarbor 影片下載器

Windows 桌面影片下載工具，可分析來源網站提供的畫質，並輸出 MP4、WebM 或 MP3。

## 下載 Windows 成品

前往此專案的 **Releases** 頁面，下載 `VideoHarbor-Windows.zip`。

完整解壓縮後執行 `VideoHarbor.exe`，不需要安裝 Python。請保留旁邊的 `_internal` 資料夾，不要只複製 EXE。更新時請解壓縮到新資料夾，避免混用舊版執行庫。

合併高畫質影音與輸出 MP3 需要另外安裝 FFmpeg，安裝方式見下方。

## 從原始碼啟動

1. 安裝 [Python 3.11 或更新版本](https://www.python.org/downloads/)。
2. 雙擊 `啟動程式.bat`。第一次啟動會建立獨立環境並安裝必要套件。
3. 貼上影片網址，按「分析影片」，選擇格式、解析度與儲存位置後下載。

合併高畫質影音與輸出 MP3 需要 FFmpeg；未安裝時，MP4/WebM 仍會改抓來源提供的最佳單一檔案。可使用 Windows 套件管理員安裝：

```powershell
winget install Gyan.FFmpeg
```

安裝後請重新啟動 VideoHarbor。

## 支援範圍

底層使用 yt-dlp，能處理 YouTube、Vimeo、Facebook、Instagram、TikTok 等許多網站公開且非 DRM 的影音。網站改版時通常只需更新 yt-dlp：

```powershell
.venv\Scripts\python.exe -m pip install --upgrade yt-dlp
```

請遵守來源網站的服務條款與著作權規範，只下載您擁有權利或已獲准保存的內容。本程式不繞過 DRM、付費牆或存取權限。

## 建立 EXE

在 PowerShell 執行：

```powershell
.\打包EXE.ps1
```

輸出位於 `dist\VideoHarbor\VideoHarbor.exe`。介面使用隨程式封裝的 Qt，不需要另外安裝 Tkinter。FFmpeg 仍需另外安裝並加入 PATH。

## 測試

```powershell
python -m unittest discover -s tests -v
```
