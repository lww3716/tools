# core/swipe_controller.py
# =======================================================================
#
#        全功能控制器 - 拟人化滑动控制器模块 (P1核心)
#
# =======================================================================
import math
import random
import re
import subprocess
import time
from typing import List, Tuple, Optional

from config import si
from utils.helpers import run_adb


# --- 贝塞尔曲线与缓动函数 ---
def cubic_bezier(p0, p1, p2, p3, t: float) -> Tuple[float, float]:
    u = 1 - t
    x = (
        (u**3 * p0[0])
        + (3 * u**2 * t * p1[0])
        + (3 * u * t**2 * p2[0])
        + (t**3 * p3[0])
    )
    y = (
        (u**3 * p0[1])
        + (3 * u**2 * t * p1[1])
        + (3 * u * t**2 * p2[1])
        + (t**3 * p3[1])
    )
    return x, y


def ease_in_out(t: float) -> float:
    return 0.5 * (1 - math.cos(math.pi * t))


class HumanSwipeController:
    def __init__(self, adb_path: str = "adb", device_serial: Optional[str] = None):
        self.adb = adb_path
        self.device = device_serial
        self.width = None
        self.height = None

    def _base_cmd(self) -> List[str]:
        cmd = [self.adb]
        if self.device:
            cmd += ["-s", self.device]
        return cmd

    def _run_and_capture(
        self, args: List[str], timeout: float = 5.0
    ) -> subprocess.CompletedProcess:
        try:
            return run_adb(self.adb, args, timeout=timeout)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                args=[self.adb] + args, returncode=124, stdout="", stderr="Timeout"
            )

    def update_device_size(self, allow_fallback: bool = True) -> Tuple[int, int]:
        args = ["shell", "wm", "size"]
        proc = self._run_and_capture(args)
        m = re.search(r"(\d+)\s*x\s*(\d+)", proc.stdout.strip())
        if m:
            self.width, self.height = int(m.group(1)), int(m.group(2))
            return self.width, self.height
        if allow_fallback:
            self.width, self.height = 1080, 2400
            return self.width, self.height
        raise RuntimeError("无法读取设备分辨率")

    def pct_to_px(self, pct: Tuple[float, float]) -> Tuple[int, int]:
        if self.width is None or self.height is None:
            self.update_device_size()
        return int(max(0, min(1, pct[0])) * self.width), int(
            max(0, min(1, pct[1])) * self.height
        )

    def adb_swipe_chain(self, points: List[Tuple[int, int]], durations_ms: List[int]):
        if not points:
            return
        base = self._base_cmd()
        try:
            with subprocess.Popen(
                base + ["shell"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=si,
                text=True,
                encoding="utf-8",
            ) as p:
                x, y = points[0]
                p.stdin.write(f"input touchscreen motionevent DOWN {x} {y}\n")
                p.stdin.flush()
                time.sleep(random.uniform(0.015, 0.04))
                for (x, y), dur_ms in zip(points[1:], durations_ms):
                    p.stdin.write(f"input touchscreen motionevent MOVE {x} {y}\n")
                    p.stdin.flush()
                    if dur_ms > 0:
                        time.sleep(dur_ms / 1000.0)
                p.stdin.write(f"input touchscreen motionevent UP {x} {y}\n")
                p.stdin.flush()
                p.stdin.close()
                p.wait(timeout=2.0)
        except Exception as e:
            raise RuntimeError(f"ADB motionevent 失败: {e}")

    def human_swipe_pct(
        self,
        start_pct: Tuple[float, float],
        end_pct: Tuple[float, float],
        duration_ms: int,
        jitter: int,
        steps_min: int,
        steps_max: int,
    ):
        if not self.device:
            raise RuntimeError("没有目标滑动设备")
        steps = random.randint(steps_min, steps_max)
        p0, p3 = self.pct_to_px(start_pct), self.pct_to_px(end_pct)
        mid_x, mid_y = (p0[0] + p3[0]) / 2, (p0[1] + p3[1]) / 2
        offset_scale = 50 + jitter * 10
        p1 = (
            (p0[0] + mid_x) / 2 + random.uniform(-offset_scale, offset_scale),
            (p0[1] + mid_y) / 2 + random.uniform(-offset_scale, offset_scale),
        )
        p2 = (
            (mid_x + p3[0]) / 2 + random.uniform(-offset_scale, offset_scale),
            (mid_y + p3[1]) / 2 + random.uniform(-offset_scale, offset_scale),
        )
        points, durations, last_t_eased = [p0], [], 0.0
        total_duration_ms_float = float(duration_ms)
        for i in range(1, steps + 1):
            t_raw = i / steps
            t_eased = ease_in_out(t_raw)
            point = cubic_bezier(
                p0, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), p3, t_eased
            )
            points.append((int(point[0]), int(point[1])))
            step_duration_ms = total_duration_ms_float * (t_eased - last_t_eased)
            durations.append(max(1, int(step_duration_ms)))
            last_t_eased = t_eased
        self.adb_swipe_chain(points, durations)
        return {"segments": len(durations), "duration_ms": sum(durations)}
