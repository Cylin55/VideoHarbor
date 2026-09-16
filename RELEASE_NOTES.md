# VideoHarbor 1.0.0

Windows 桌面影片下載器，提供網址分析、可用解析度選擇、MP4/WebM/MP3 輸出、下載進度與取消功能。

## 下載與啟動

1. 下載本 Release 的 `VideoHarbor-Windows.zip`。
2. 將全部內容解壓縮到新資料夾。
3. 執行 `VideoHarbor.exe`；旁邊的 `_internal` 資料夾必須保留。

不需安裝 Python。程式使用封裝的 Qt 介面，不依賴 Tkinter。

## FFmpeg

MP3 與高畫質影音合併需要 FFmpeg。可在 Windows 終端機執行：

```powershell
winget install Gyan.FFmpeg
```

安裝後重新啟動程式。沒有 FFmpeg 時，影片下載會改選來源提供的單一檔案，實際畫質及格式受來源限制。

## 注意事項

- 僅適用於您有權下載且平台允許保存的內容。
- 不支援繞過 DRM、登入權限或付費牆。
- 各平台支援情況受來源網站及 yt-dlp 相容性影響，並非所有網址都能下載。
