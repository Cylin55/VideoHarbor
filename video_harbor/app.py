from __future__ import annotations

import os
import queue
import sys
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget)

from .core import DownloadCancelled, download_media, format_duration, inspect_media


STYLE = """
QWidget { background: #0b1020; color: #f5f7ff; font-family: "Microsoft JhengHei UI"; font-size: 14px; }
QFrame#card { background: #151c32; border-radius: 12px; }
QFrame#mediaInfo { background: #11182b; border-radius: 8px; }
QLineEdit, QComboBox { background: #202943; border: 1px solid #2a3658; border-radius: 7px; padding: 10px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #6d5dfc; }
QComboBox QAbstractItemView { background: #202943; color: #f5f7ff; selection-background-color: #6d5dfc; }
QPushButton { background: #202943; border: none; border-radius: 7px; padding: 10px 18px; font-weight: 600; }
QPushButton:hover { background: #2b3657; } QPushButton:disabled { color: #68728a; background: #192138; }
QPushButton#accent { background: #6d5dfc; } QPushButton#accent:hover { background: #8174ff; }
QProgressBar { background: #202943; border: none; border-radius: 5px; height: 10px; text-align: center; color: transparent; }
QProgressBar::chunk { background: #6d5dfc; border-radius: 5px; }
"""


class VideoHarborWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VideoHarbor 影片下載器")
        self.resize(840, 680)
        self.setMinimumSize(720, 620)
        self._events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._cancel_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._current_file: Path | None = None
        self._resolution_map: dict[str, int | None] = {"最佳畫質": None}
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_events)
        self._timer.start(100)

    def _text(self, value: str, size: int = 14, muted: bool = False, bold: bool = False) -> QLabel:
        label = QLabel(value)
        label.setStyleSheet(f"color: {'#9da9c4' if muted else '#f5f7ff'}; background: transparent;")
        font = QFont("Microsoft JhengHei UI", size)
        font.setBold(bold)
        label.setFont(font)
        return label

    def _button(self, text: str, callback, accent: bool = False) -> QPushButton:
        button = QPushButton(text)
        if accent:
            button.setObjectName("accent")
        button.clicked.connect(callback)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(36, 28, 36, 24)
        outer.setSpacing(0)
        outer.addWidget(self._text("VideoHarbor", 25, bold=True))
        outer.addWidget(self._text("跨平台影片下載工具", 11, muted=True))
        outer.addSpacing(22)
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 23, 25, 23)
        layout.setSpacing(9)
        outer.addWidget(card, 1)
        layout.addWidget(self._text("影片網址", 10, bold=True))
        url_row = QHBoxLayout()
        self.url_entry = QLineEdit(placeholderText="https://...")
        url_row.addWidget(self.url_entry, 1)
        url_row.addWidget(self._button("貼上", self._paste))
        self.analyze_button = self._button("分析影片", self._analyze, True)
        url_row.addWidget(self.analyze_button)
        layout.addLayout(url_row)
        layout.addSpacing(8)
        info = QFrame(objectName="mediaInfo")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(16, 13, 16, 13)
        self.info_title = self._text("尚未分析影片", 12, bold=True)
        self.info_title.setWordWrap(True)
        self.info_meta = self._text("支援 yt-dlp 可處理的公開影音網站", 9, muted=True)
        info_layout.addWidget(self.info_title)
        info_layout.addWidget(self.info_meta)
        layout.addWidget(info)
        layout.addSpacing(8)
        choices = QHBoxLayout()
        fmt = QVBoxLayout()
        fmt.addWidget(self._text("輸出格式", 10, bold=True))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4", "WEBM", "MP3"])
        self.format_combo.currentTextChanged.connect(self._format_changed)
        fmt.addWidget(self.format_combo)
        choices.addLayout(fmt, 1)
        res = QVBoxLayout()
        res.addWidget(self._text("解析度", 10, bold=True))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItem("最佳畫質")
        res.addWidget(self.resolution_combo)
        choices.addLayout(res, 1)
        layout.addLayout(choices)
        layout.addSpacing(8)
        layout.addWidget(self._text("儲存位置", 10, bold=True))
        folder_row = QHBoxLayout()
        self.folder_entry = QLineEdit(str(Path.home() / "Downloads"))
        folder_row.addWidget(self.folder_entry, 1)
        folder_row.addWidget(self._button("瀏覽", self._choose_folder))
        layout.addLayout(folder_row)
        layout.addSpacing(8)
        actions = QHBoxLayout()
        self.download_button = self._button("開始下載", self._download, True)
        self.cancel_button = self._button("取消", self._cancel)
        self.cancel_button.setEnabled(False)
        self.open_button = self._button("開啟資料夾", self._open_folder)
        actions.addWidget(self.download_button)
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        actions.addWidget(self.open_button)
        layout.addLayout(actions)
        layout.addSpacing(8)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        self.status_label = self._text("準備就緒", 10, bold=True)
        self.status_label.setStyleSheet("color: #31c48d; background: transparent;")
        layout.addWidget(self.status_label)
        self.detail_label = self._text("貼上影片網址，先按「分析影片」取得可用畫質。", 9, muted=True)
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)
        outer.addSpacing(14)
        legal = self._text("請只下載您擁有權利或平台允許下載的內容；不支援 DRM 保護影片。", 9, muted=True)
        legal.setWordWrap(True)
        outer.addWidget(legal)

    def _paste(self) -> None:
        text = QApplication.clipboard().text().strip()
        if text:
            self.url_entry.setText(text)
        else:
            QMessageBox.information(self, "剪貼簿", "剪貼簿中沒有文字。")

    def _choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "選擇儲存位置", self.folder_entry.text())
        if path:
            self.folder_entry.setText(path)

    def _set_busy(self, busy: bool, cancellable: bool = False) -> None:
        self.analyze_button.setEnabled(not busy)
        self.download_button.setEnabled(not busy)
        self.cancel_button.setEnabled(cancellable)

    def _status(self, title: str, detail: str) -> None:
        self.status_label.setText(title)
        self.detail_label.setText(detail)

    def _analyze(self) -> None:
        if self._worker and self._worker.is_alive(): return
        self._set_busy(True)
        self._status("正在分析…", "正在向來源網站取得影片資訊與可用畫質。")
        self._worker = threading.Thread(target=self._analyze_worker, args=(self.url_entry.text(),), daemon=True)
        self._worker.start()

    def _analyze_worker(self, url: str) -> None:
        try: self._events.put(("info", inspect_media(url)))
        except Exception as exc: self._events.put(("error", str(exc)))

    def _format_changed(self, value: str) -> None:
        audio = value == "MP3"
        self.resolution_combo.setEnabled(not audio)
        if audio:
            if self.resolution_combo.findText("不適用（音訊）") < 0: self.resolution_combo.addItem("不適用（音訊）")
            self.resolution_combo.setCurrentText("不適用（音訊）")
        elif self.resolution_combo.currentText() == "不適用（音訊）": self.resolution_combo.setCurrentIndex(0)

    def _download(self) -> None:
        if self._worker and self._worker.is_alive(): return
        folder = self.folder_entry.text().strip()
        if not folder:
            QMessageBox.warning(self, "儲存位置", "請選擇儲存位置。")
            return
        self._cancel_event.clear()
        self.progress.setValue(0)
        self._set_busy(True, True)
        self._status("準備下載…", "正在連線至來源網站。")
        container = self.format_combo.currentText()
        height = None if container == "MP3" else self._resolution_map.get(self.resolution_combo.currentText())
        self._worker = threading.Thread(target=self._download_worker,
            args=(self.url_entry.text(), Path(folder), container, height), daemon=True)
        self._worker.start()

    def _download_worker(self, url: str, folder: Path, container: str, height: int | None) -> None:
        try:
            path = download_media(url, folder, container, height,
                lambda data: self._events.put(("progress", data)), self._cancel_event)
            self._events.put(("done", path))
        except DownloadCancelled as exc: self._events.put(("cancelled", str(exc)))
        except Exception as exc: self._events.put(("error", str(exc)))

    def _cancel(self) -> None:
        self._cancel_event.set()
        self._status("正在取消…", "目前的下載會在下一個資料區塊停止。")
        self.cancel_button.setEnabled(False)

    def _handle_progress(self, data: dict[str, Any]) -> None:
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            if total: self.progress.setValue(min(100, int(data.get("downloaded_bytes", 0) * 100 / total)))
            self._status("正在下載", f"速度 {data.get('_speed_str', '--')}  ·  剩餘時間 {data.get('_eta_str', '--')}")
        elif data.get("status") == "finished":
            self.progress.setValue(100)
            self._status("正在處理檔案…", "下載完成，正在合併影音或轉換格式。")

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self._events.get_nowait()
                if kind == "info":
                    values = ["最佳畫質", *(f"{h}p" for h in payload.resolutions)]
                    self._resolution_map = {"最佳畫質": None, **{f"{h}p": h for h in payload.resolutions}}
                    self.resolution_combo.clear(); self.resolution_combo.addItems(values)
                    if self.format_combo.currentText() == "MP3": self._format_changed("MP3")
                    self.info_title.setText(payload.title)
                    self.info_meta.setText(f"{payload.uploader}  ·  {format_duration(payload.duration)}  ·  {len(payload.resolutions)} 種畫質")
                    self._status("分析完成", "已載入可用解析度，可以開始下載。"); self._set_busy(False)
                elif kind == "progress": self._handle_progress(payload)
                elif kind == "done":
                    self._current_file = payload; self.progress.setValue(100)
                    self._status("下載完成", f"已儲存至：{payload}"); self._set_busy(False)
                elif kind == "cancelled": self._status("已取消", payload); self._set_busy(False)
                elif kind == "error":
                    self._status("發生錯誤", payload); self._set_busy(False)
                    QMessageBox.critical(self, "操作失敗", payload)
        except queue.Empty: pass

    def _open_folder(self) -> None:
        folder = self._current_file.parent if self._current_file and self._current_file.parent.exists() else Path(self.folder_entry.text())
        if folder.exists(): os.startfile(folder)
        else: QMessageBox.warning(self, "找不到資料夾", "指定的資料夾尚不存在。")

    def closeEvent(self, event: QCloseEvent) -> None:
        self._cancel_event.set(); event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = VideoHarborWindow()
    window.show()
    raise SystemExit(app.exec())
