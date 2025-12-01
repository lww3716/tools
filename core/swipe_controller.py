# core/swipe_controller.py
# =======================================================================
#   2025年12月 终极核弹级拟人滑动（Flick专用版）
#   解决：兼容长距离滑动，消除末端停顿，模拟手指“甩动”离屏时的非零速度
# =======================================================================
import math
import random
import re
import subprocess
import time
from typing import List, Tuple, Optional, Dict, Any

from config import si
from utils.helpers import run_adb


# ---------- 三阶贝塞尔曲线 ----------
def cubic_bezier(
    p0: Tuple[int, int],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[int, int],
    t: float,
) -> Tuple[float, float]:
    u = 1 - t
    x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
    y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
    return x, y


# ---------- 智能甩动曲线 (Smart Flick) ----------
def smart_flick(t: float) -> float:
    """
    智能甩动曲线。
    数学公式：f(t) = t + A * t * (1 - t)

    特点：
    1. t=0 时，速度极快（爆发力）。
    2. t=1 时，速度依然 > 0（关键！）。
    3. 这模拟了手指在克服摩擦力后，带着动能离开屏幕的过程。

    相比 EaseOutCubic/Quint 在 t=1 时速度归零，这个函数能彻底根治“停顿感”。
    """
    # 系数 0.5 决定了曲线的弯曲程度。
    # 0.5 意味着起步速度是匀速的 1.5 倍，结束速度是匀速的 0.5 倍。
    # 保证了“前快后慢”但“绝不停止”。
    return t + 0.5 * t * (1 - t)


class HumanSwipeController:
    def __init__(self, adb_path: str = "adb", device_serial: Optional[str] = None):
        self.adb = adb_path
        self.device = device_serial
        self.width: Optional[int] = None
        self.height: Optional[int] = None

    def _base_cmd(self) -> List[str]:
        cmd = [self.adb]
        if self.device:
            cmd += ["-s", self.device]
        return cmd

    def update_device_size(self, allow_fallback: bool = True) -> Tuple[int, int]:
        try:
            proc = run_adb(self.adb, ["shell", "wm", "size"])
            m = re.search(r"(\d+)\s*x\s*(\d+)", proc.stdout.strip())
            if m:
                self.width, self.height = int(m.group(1)), int(m.group(2))
            else:
                self.width, self.height = 1080, 2400
        except Exception:
            self.width, self.height = 1080, 2400
        return self.width, self.height

    def pct_to_px(self, pct: Tuple[float, float]) -> Tuple[int, int]:
        if self.width is None or self.height is None:
            self.update_device_size()
        return int(pct[0] * self.width), int(pct[1] * self.height)

    def adb_swipe_chain(self, points: List[Tuple[int, int]], durations_ms: List[int]):
        if len(points) < 2:
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
                # Down: 几乎无延迟，模拟一触即发
                p.stdin.write(f"input touchscreen motionevent DOWN {x} {y}\n")
                p.stdin.flush()
                # 极短的接触时间，避免被识别为长按
                time.sleep(random.uniform(0.005, 0.01))

                for (x, y), dur_ms in zip(points[1:], durations_ms):
                    p.stdin.write(f"input touchscreen motionevent MOVE {x} {y}\n")
                    p.stdin.flush()
                    if dur_ms > 0:
                        time.sleep(dur_ms / 1000.0)

                # Up: 直接抬起，不等待，保留残影速度
                p.stdin.write(f"input touchscreen motionevent UP {x} {y}\n")
                p.stdin.flush()
                p.stdin.close()
                p.wait(timeout=2.0)
        except Exception as e:
            print(f"[滑动器] motionevent 异常: {e}")

    def human_swipe_pct(
        self,
        start_pct: Tuple[float, float],
        end_pct: Tuple[float, float],
        duration_ms: int,
        jitter: int,
        steps_min: int,
        steps_max: int,
    ) -> Dict[str, Any]:
        if not self.device:
            raise RuntimeError("没有目标滑动设备")

        steps = random.randint(steps_min, steps_max)
        p0 = self.pct_to_px(start_pct)
        p3 = self.pct_to_px(end_pct)

        # 稍微减小偏移，让长距离滑动更稳定
        offset_scale = 60 + jitter * 10
        mid_x = (p0[0] + p3[0]) / 2

        p1 = (
            mid_x + random.uniform(-offset_scale, offset_scale),
            p0[1] + random.uniform(-offset_scale * 0.8, offset_scale * 0.2),
        )
        p2 = (
            mid_x + random.uniform(-offset_scale, offset_scale),
            p3[1] + random.uniform(-offset_scale * 0.4, offset_scale * 0.6),
        )

        points = [p0]
        durations = []
        last_t = 0.0
        total_duration = float(duration_ms)

        last_pt_int = (int(p0[0]), int(p0[1]))

        for i in range(1, steps + 1):
            t_raw = i / steps

            # 使用智能甩动曲线，确保 t=1 时依然有斜率（速度）
            t_eased = smart_flick(t_raw)

            pt = cubic_bezier(p0, p1, p2, p3, t_eased)
            curr_pt_int = (int(pt[0]), int(pt[1]))

            # 坐标去重：这是防止卡顿的第二道防线
            if curr_pt_int == last_pt_int:
                continue

            points.append(curr_pt_int)

            step_dur = total_duration * (t_eased - last_t)
            durations.append(max(1, int(step_dur)))

            last_t = t_eased
            last_pt_int = curr_pt_int

        self.adb_swipe_chain(points, durations)

        return {
            "segments": len(durations),
            "duration_ms": sum(durations),
            "start": start_pct,
            "end": end_pct,
        }
