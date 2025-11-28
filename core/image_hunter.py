# core/image_hunter.py
# =======================================================================
#
#        全功能控制器 - 图像狩猎器模块 (P2)
#
# =======================================================================
import threading
import random
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

from PyQt6.QtCore import QObject, pyqtSignal

from config import IMAGE_FOLDER_HUNTER
from utils.helpers import get_window_region, find_image_with_opencv
from .adb_controller import AdbController


class ImageHunter(QObject):
    log_message = pyqtSignal(str)
    stopped = pyqtSignal()
    started = pyqtSignal()

    def __init__(self, controller: AdbController):
        super().__init__()
        self.controller = controller
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.params: Dict[str, Any] = {}
        self.target_images_by_action: Dict[str, List[str]] = {
            "a_click": [],
            "b_back": [],
            "c_reserved": [],
            "d_reserved": [],
        }

    def _load_target_images(self):
        base, action_map = IMAGE_FOLDER_HUNTER, {
            "a": "a_click",
            "b": "b_back",
            "c": "c_reserved",
            "d": "d_reserved",
        }
        for folder_name, action_key in action_map.items():
            folder_path = base / folder_name
            if folder_path.is_dir():
                images = [str(p) for p in folder_path.glob("*.png") if p.exists()]
                self.target_images_by_action[action_key] = images
                self.log_message.emit(
                    f"[狩猎器] 从 {folder_name} 加载了 {len(images)} 张图片 -> {action_key}"
                )
            else:
                self.log_message.emit(
                    f"[狩猎器] 提示：未找到文件夹 {folder_path}，跳过。"
                )

    def start(self, params: Dict[str, Any], window_title: str):
        if self._thread and self._thread.is_alive():
            return
        self._load_target_images()
        if not any(self.target_images_by_action.values()):
            self.log_message.emit(
                "[狩猎器] 错误：没有可供查找的目标图片 (a, b, c, d 文件夹为空)。"
            )
            return

        self.params = params
        self.target_window_title = window_title
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.log_message.emit(f"[狩猎器] 狩猎模式启动：目标窗口 '{window_title}'")
        self.started.emit()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self.log_message.emit("[狩猎器] 狩猎模式已停止。")
            self._thread = None
        self.stopped.emit()

    def _find_priority_match(
        self, region: Tuple[int, int, int, int]
    ) -> Optional[Tuple[Any, str, str]]:
        conf = self.params.get("conf", 0.8)
        # 优先检测A类
        a_matches = [
            (box, path)
            for path in self.target_images_by_action["a_click"]
            if (box := find_image_with_opencv(path, confidence=conf, region=region))
        ]
        if a_matches:
            a_matches.sort(key=lambda m: Path(m[1]).name)  # 按文件名排序
            return a_matches[0][0], a_matches[0][1], "a_click"

        # 检测其他类别
        for action_key in ["b_back", "c_reserved", "d_reserved"]:
            for img_path in self.target_images_by_action.get(action_key, []):
                if box := find_image_with_opencv(
                    img_path, confidence=conf, region=region
                ):
                    return box, img_path, action_key
        return None

    def _translate_pc_to_phone_coords(
        self, pc_x: int, pc_y: int, region: Tuple[int, int, int, int]
    ) -> Tuple[int, int]:
        rl, rt, rw, rh = region
        ph_w, ph_h = self.controller.width, self.controller.height
        rel_x = (pc_x - rl) / rw
        rel_y = (pc_y - rt) / rh
        return int(max(0, min(1, rel_x)) * ph_w), int(max(0, min(1, rel_y)) * ph_h)

    def _get_random_point_in_box(self, box: Any) -> Tuple[int, int]:
        p = self.params
        off_x = box.width * random.uniform(p.get("x_min", 0.3), p.get("x_max", 0.7))
        off_y = box.height * random.uniform(p.get("y_min", 0.3), p.get("y_max", 0.7))
        return int(box.left + off_x), int(box.top + off_y)

    def _perform_action(self, box: Any, img_path: str, action_key: str):
        img_name = Path(img_path).name
        p = self.params
        wait_time = random.uniform(p.get("min_s", 5.0), p.get("max_s", 10.0))
        self.log_message.emit(
            f"[狩猎器] 发现 {action_key} 目标 {img_name}，将在 {wait_time:.1f} 秒后行动..."
        )

        self._stop_event.wait(wait_time)
        if self._stop_event.is_set():
            return

        current_region = get_window_region(self.target_window_title)
        if not current_region:
            self.log_message.emit(
                f"[狩猎器] 动作取消：窗口 '{self.target_window_title}' 已消失。"
            )
            return

        if not find_image_with_opencv(
            img_path, confidence=p.get("conf", 0.8), region=current_region
        ):
            self.log_message.emit(
                f"[狩猎器] 动作取消：目标 {img_name} 在等待后消失了。"
            )
            return

        try:
            if action_key == "a_click":
                pc_x, pc_y = self._get_random_point_in_box(box)
                phone_x, phone_y = self._translate_pc_to_phone_coords(
                    pc_x, pc_y, current_region
                )
                self.controller.human_click_at_coords(phone_x, phone_y)
                self.log_message.emit(
                    f"[狩猎器] ✓ 点击 {img_name} 成功 (坐标 {phone_x}, {phone_y})"
                )
            elif action_key == "b_back":
                self.controller.human_click_back()
                self.log_message.emit(f"[狩猎器] ✓ 返回 成功 (触发于 {img_name})")
            else:
                self.log_message.emit(
                    f"[狩猎器] ✓ 备用动作 {action_key[0]} 已记录 (目标 {img_name})"
                )
        except Exception as e:
            self.log_message.emit(f"[狩猎器] 执行失败: {e}")

    def _loop(self):
        while not self._stop_event.is_set():
            region = get_window_region(self.target_window_title)
            if not region:
                if self.target_window_title:
                    self.log_message.emit(
                        f"[狩猎器] 等待窗口 '{self.target_window_title}' 出现..."
                    )
                self._stop_event.wait(2.0)
                continue

            match = self._find_priority_match(region)
            if match:
                self._perform_action(match[0], match[1], match[2])

            self._stop_event.wait(0.5)
