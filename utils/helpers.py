# utils/helpers.py
# =======================================================================
#
#        全功能控制器 - 共享助手函数模块
#
# =======================================================================
import os
import shutil
import subprocess
from typing import List, Tuple, Optional
from collections import namedtuple

import cv2
import numpy as np
from mss import mss
import win32gui

from config import POSSIBLE_ADB_PATHS, si

Box = namedtuple("Box", ["left", "top", "width", "height"])


def find_image_with_opencv(
    template_path: str,
    confidence: float,
    region: Optional[Tuple[int, int, int, int]] = None,
) -> Optional[Box]:
    try:
        template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
        if template is None:
            return None
        template_h, template_w = template.shape[:2]

        mask = None
        if template.shape[2] == 4:
            alpha_channel = template[:, :, 3]
            _, mask = cv2.threshold(alpha_channel, 0, 255, cv2.THRESH_BINARY)
            template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)

        with mss() as sct:
            monitor = (
                {
                    "top": region[1],
                    "left": region[0],
                    "width": region[2],
                    "height": region[3],
                }
                if region
                else sct.monitors[0]
            )
            screenshot_img = sct.grab(monitor)
            screenshot = np.array(screenshot_img)
            screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

        method = cv2.TM_CCOEFF_NORMED
        result = (
            cv2.matchTemplate(screenshot_bgr, template, method, mask=mask)
            if mask is not None
            else cv2.matchTemplate(screenshot_bgr, template, method)
        )
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= confidence:
            top_left = max_loc
            final_left = top_left[0] + region[0] if region else top_left[0]
            final_top = top_left[1] + region[1] if region else top_left[1]
            return Box(
                left=final_left, top=final_top, width=template_w, height=template_h
            )
    except Exception:
        return None
    return None


def find_adb() -> Optional[str]:
    exe = shutil.which("adb")
    if exe:
        return exe
    for p in POSSIBLE_ADB_PATHS:
        if os.path.isfile(p):
            return p
    return None


def run_adb(
    adb_path: str, args: List[str], timeout: Optional[float] = None
) -> subprocess.CompletedProcess:
    cmd = [adb_path] + args
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        startupinfo=si,
        encoding="utf-8",
        errors="ignore",
    )


def get_connected_devices(adb_path: str) -> List[str]:
    try:
        p = run_adb(adb_path, ["devices"])
        lines = p.stdout.strip().splitlines()
        return [
            line.split()[0]
            for line in lines[1:]
            if "device" in line and len(line.split()) > 1
        ]
    except Exception:
        return []


def get_window_region(window_title: str) -> Optional[Tuple[int, int, int, int]]:
    try:
        hwnd = win32gui.FindWindow(None, window_title)
        if not hwnd or win32gui.IsIconic(hwnd):
            return None
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = right - left, bottom - top
        return (left, top, width, height) if width > 0 and height > 0 else None
    except Exception:
        return None
