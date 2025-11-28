# core/adb_controller.py
# =======================================================================
#
#        全功能控制器 - 基础ADB控制器模块 (P2核心)
#
# =======================================================================
import subprocess
import random
import re
from typing import List, Optional, Dict

from config import ID_TO_NAME, si
from utils.helpers import run_adb


class AdbController:
    def __init__(self, adb_path: str):
        self.adb = adb_path
        self.device_id: Optional[str] = None
        self.width, self.height = 1080, 2400

    def get_connected_devices(self) -> Dict[str, str]:
        try:
            lines = run_adb(self.adb, ["devices"]).stdout.strip().splitlines()
            return {
                line.split()[0]: ID_TO_NAME.get(line.split()[0], line.split()[0])
                for line in lines[1:]
                if "device" in line
            }
        except Exception:
            return {}

    def set_device(self, device_id: str):
        self.device_id = device_id
        self._update_device_size()

    def _base_cmd(self) -> List[str]:
        if not self.device_id:
            raise ValueError("未设置目标设备")
        return [self.adb, "-s", self.device_id]

    def _update_device_size(self):
        try:
            out = subprocess.run(
                self._base_cmd() + ["shell", "wm", "size"],
                stdout=subprocess.PIPE,
                text=True,
                timeout=3.0,
                startupinfo=si,
            ).stdout.strip()
            m = re.search(r"(\d+)\s*x\s*(\d+)", out)
            if m:
                self.width, self.height = int(m.group(1)), int(m.group(2))
        except Exception:
            pass

    def human_click_at_coords(self, phone_x: int, phone_y: int):
        duration = random.randint(40, 90)
        cmd = self._base_cmd() + [
            "shell",
            "input",
            "swipe",
            str(phone_x),
            str(phone_y),
            str(phone_x),
            str(phone_y),
            str(duration),
        ]
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=si
        )

    def human_click_back(self):
        cmd = self._base_cmd() + ["shell", "input", "keyevent", "4"]
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=si
        )
