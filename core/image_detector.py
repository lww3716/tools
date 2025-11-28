# core/image_detector.py
# =======================================================================
#
#        全功能控制器 - 图像检测器模块 (P1)
#
# =======================================================================
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from utils.helpers import get_window_region, find_image_with_opencv


class ImageDetector(QObject):
    status_updated = pyqtSignal(bool)
    interrupt_requested = pyqtSignal()

    def __init__(self, folder: Path, poll_interval=1.5):
        super().__init__()
        self.folder = folder
        self._running = threading.Event()
        self._stop = threading.Event()
        self.found_event = threading.Event()
        self.poll_interval = poll_interval
        self.confidence = 0.8
        self.target_window_title = ""
        self._thread = None

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop, daemon=True, name="ImageDetector"
            )
            self._thread.start()

    def enable(self, window_title: str):
        self.target_window_title = window_title
        self._running.set()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self._thread = None

    def disable(self):
        self._running.clear()
        self.found_event.clear()
        self.status_updated.emit(False)

    def _loop(self):
        if not self.folder.is_dir():
            self.stop()
            return

        while not self._stop.is_set():
            if not self._running.is_set() or not self.target_window_title:
                time.sleep(0.2)
                continue

            region = get_window_region(self.target_window_title)
            if region is None:
                if self.found_event.is_set():
                    self.found_event.clear()
                    self.status_updated.emit(False)
                time.sleep(self.poll_interval)
                continue

            found = any(
                find_image_with_opencv(
                    str(path), confidence=self.confidence, region=region
                )
                for path in self.folder.glob("*.png")
                if path.exists()
            )

            if found and not self.found_event.is_set():
                self.found_event.set()
                self.status_updated.emit(True)
                self.interrupt_requested.emit()
            elif not found and self.found_event.is_set():
                self.found_event.clear()
                self.status_updated.emit(False)

            time.sleep(self.poll_interval)
