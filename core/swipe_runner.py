# core/swipe_runner.py
# =======================================================================
#
#        全功能控制器 - 滑动调度器模块 (P1) - V5.3逻辑重构版
#
# =======================================================================
import threading
import random
import time
from typing import Dict, Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from config import ID_TO_NAME, IMAGE_FOLDER_SWIPER_GATE
from utils.helpers import get_window_region, find_image_with_opencv
from .swipe_controller import HumanSwipeController
from .image_detector import ImageDetector


class SwipeRunner(QObject):
    log_message = pyqtSignal(str)
    status_updated = pyqtSignal(str)
    countdown_updated = pyqtSignal(str)
    stopped = pyqtSignal()
    started = pyqtSignal()

    swipe_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self, controller: HumanSwipeController, detector: Optional[ImageDetector]
    ):
        super().__init__()
        self.ctrl = controller
        self.detector = detector
        self._running = False
        self.remaining_time = 0
        self.swipe_count = 0
        self.params = {}

        self.countdown_timer = QTimer()
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self._update_countdown)

        self.swipe_finished.connect(self._on_swipe_done)
        self.error_occurred.connect(self._on_swipe_error)

    def start(self, params: Dict[str, Any], window_title: str):
        if self._running:
            return
        if not self.ctrl.device:
            self.log_message.emit("错误: 滑动目标设备未设置。")
            return

        self.params = params
        self.params["window_title"] = window_title  # 存储窗口标题供后续使用
        device_name = ID_TO_NAME.get(self.ctrl.device, self.ctrl.device[-8:])
        self._running = True
        self.swipe_count = 0
        self.log_message.emit(f"[滑动器] 已启动循环滑动，目标: {device_name}")
        self.started.emit()
        # 立即执行第一次滑动，而不是先等待
        self._do_swipe()

    def stop(self):
        if not self._running:
            return
        self._running = False
        self.countdown_timer.stop()
        QTimer.singleShot(0, self.stop_related_timers) # 确保所有定时器都被停止
        self.status_updated.emit(f"状态：已停止 (共 {self.swipe_count} 次)")
        self.countdown_updated.emit("下次循环倒计时：-- 秒")
        self.log_message.emit("[滑动器] 循环滑动已停止")
        self.stopped.emit()
    
    def stop_related_timers(self):
        # 这是一个辅助函数，确保在事件循环中安全地停止所有可能的定时器
        # 在这个版本中，主要由 self.countdown_timer.stop() 和 self._running = False 控制，
        # 但保留这个结构以备将来扩展更复杂的定时器。
        pass

    def interrupt_countdown(self):
        if not self._running:
            return
        self.countdown_timer.stop()
        self.log_message.emit("[滑动器] 接收到P1图像检测中断信号，立即缩短间隔...")
        self._schedule_next_swipe(is_interrupted=True)

    def _check_for_gate_image(self) -> bool:
        """检查P1启动条件的图像是否存在。"""
        window_title = self.params.get("window_title")
        if not window_title:
            return True  # 如果没有窗口标题，无法检测，默认通过

        region = get_window_region(window_title)
        if not region:
            return False  # 窗口不存在，视为不满足条件

        confidence = self.params.get("confidence", 0.8)

        if not IMAGE_FOLDER_SWIPER_GATE.is_dir(): return True
        image_list = list(IMAGE_FOLDER_SWIPER_GATE.glob("*.png"))
        if not image_list: return True

        for img_path in image_list:
            if find_image_with_opencv(str(img_path), confidence=confidence, region=region):
                return True
        return False

    def _schedule_next_swipe(self, is_interrupted: bool = False):
        if not self._running:
            return

        is_gate_enabled = self.params.get("p1_start_condition_enabled", False)
        if is_gate_enabled:
            if not self._check_for_gate_image():
                self.status_updated.emit("状态：等待P1启动门图像...")
                self.countdown_updated.emit("下次循环倒计时：--")
                # 条件不满足，1.5秒后再次尝试调度
                QTimer.singleShot(1500, lambda: self._schedule_next_swipe(is_interrupted=False))
                return

        try:
            min_interval, max_interval = (self.params["interval_min"], self.params["interval_max"])
            is_detection_enabled = self.params["detection_enabled"]
            is_image_found = self.detector.found_event.is_set() if self.detector else False

            if is_detection_enabled and is_image_found:
                interval = random.uniform(2.0, 4.0)
                log_msg = f"[滑动器] ✓ P1加速已触发，缩短间隔: {interval:.1f}s"
                self.log_message.emit(log_msg)
            else:
                interval = random.uniform(min_interval, max_interval)
                if is_interrupted:
                    self.log_message.emit("[滑动器] 中断时P1目标图片已消失，保持正常间隔。")

            self.remaining_time = max(1, int(interval))
            self.status_updated.emit(f"状态：运行中 — 次数 {self.swipe_count}")
            self.countdown_timer.start()
            self._update_countdown()

        except Exception as e:
            self.log_message.emit(f"[滑动器] 调度参数错误: {e}")
            self.stop()

    def _update_countdown(self):
        if not self._running:
            return
        if self.remaining_time <= 0:
            self.countdown_timer.stop()
            self._do_swipe()
        else:
            self.countdown_updated.emit(f"下次循环倒计时：{self.remaining_time} 秒")
            self.remaining_time -= 1

    def _do_swipe(self):
        if not self._running or not self.ctrl.device:
            self.log_message.emit("[滑动器] 滑动失败: 目标设备已断开或未选中。")
            self.stop()
            return
        threading.Thread(target=self._run_swipe_in_thread, daemon=True).start()

    def _run_swipe_in_thread(self):
        try:
            p = self.params
            start_x, start_y, end_x, end_y = (p["start_x"], p["start_y"], p["end_x"], p["end_y"])
            max_offset = p["coord_offset"] / 100.0

            start_pct = (
                max(0.0, min(1.0, start_x + random.uniform(-max_offset, max_offset))),
                max(0.0, min(1.0, start_y + random.uniform(-max_offset, max_offset))),
            )
            end_pct = (
                max(0.0, min(1.0, end_x + random.uniform(-max_offset, max_offset))),
                max(0.0, min(1.0, end_y + random.uniform(-max_offset, max_offset))),
            )

            duration_ms = random.randint(p["duration_min"], p["duration_max"])
            res = self.ctrl.human_swipe_pct(
                start_pct, end_pct, duration_ms, p["jitter"], p["steps_min"], p["steps_max"]
            )
            self.swipe_finished.emit(res)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _on_swipe_done(self, result: dict):
        if not self._running:
            return
        self.swipe_count += 1
        self.log_message.emit(f"[滑动器] 滑动完成: {result}")
        self._schedule_next_swipe(is_interrupted=False)

    def _on_swipe_error(self, error_message: str):
        self.log_message.emit(f"[滑动器] 滑动操作异常: {error_message}")
        self.stop()