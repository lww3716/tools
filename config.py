# config.py
# =======================================================================
#
#        全功能控制器 - 共享配置文件
#
# =======================================================================
import os
from pathlib import Path

# 1. 设备映射 (共享)
DEVICE_MAP = {
    "嵬嵬手机": "mn85nrjbzlov4pjz",
    "李莉手机": "CYFQP7LF4PINS8GA",
    "大屏手机": "a210da8f",
    "五里店小手机": "eeec90207d28",
    "lili新手机": "9HCIQ8YXEIC6TGQK",
}
ID_TO_NAME = {v: k for k, v in DEVICE_MAP.items()}

# 2. 路径配置 (共享)
SCRCPY_PATH = r"C:\scrcpy-win64-v2.6.1\scrcpy.exe"
POSSIBLE_ADB_PATHS = [
    r"C:\scrcpy-win64-v2.6.1\adb.exe",
    r"C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe",
    r"C:\Program Files\Android\android-sdk\platform-tools\adb.exe",
]

# 3. (V2) 统一的资源文件夹和配置文件
BASE_CONFIG_FOLDER = Path(r"C:\lww1")
CONFIG_FILE_COMBINED = BASE_CONFIG_FOLDER / "combined_profiles.json"
IMAGE_FOLDER_SWIPER = BASE_CONFIG_FOLDER
IMAGE_FOLDER_HUNTER = BASE_CONFIG_FOLDER
IMAGE_FOLDER_SWIPER_GATE = BASE_CONFIG_FOLDER / "e"
DEFAULT_PROFILE_NAME = "默认用户"

# 4. 隐藏 subprocess 窗口 (共享)
if os.name == "nt":
    import subprocess

    si = subprocess.STARTUPINFO()
    try:
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
    except AttributeError:
        si = None
else:
    si = None
