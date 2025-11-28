# ui/main_window.py
# =======================================================================
#
#        全功能控制器 - 主窗口UI模块 (v6.1 - 按钮美化版)
#
# =======================================================================
import json
import time
import subprocess
from pathlib import Path
import os
import re

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QGroupBox,
    QLabel,
    QTextEdit,
    QGridLayout,
    QMessageBox,
    QComboBox,
    QFileDialog,
    QInputDialog,
)
from PyQt6.QtCore import QTimer

# 从自定义模块中导入
from config import (
    ID_TO_NAME,
    SCRCPY_PATH,
    BASE_CONFIG_FOLDER,
    CONFIG_FILE_COMBINED,
    IMAGE_FOLDER_SWIPER,
    DEFAULT_PROFILE_NAME,
)
from utils.helpers import find_adb, get_connected_devices, run_adb
from core.swipe_controller import HumanSwipeController
from core.adb_controller import AdbController
from core.image_detector import ImageDetector
from core.swipe_runner import SwipeRunner
from core.image_hunter import ImageHunter
from .dialogs import SwiperSettingsDialog, HunterSettingsDialog


class SwipeApp_PyQt(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("全功能控制器 v6.1 (按钮美化版)")
        self.setGeometry(100, 100, 1100, 750)

        self._define_stylesheets()
        self.is_dark_theme = True

        # --- 数据与状态 ---
        self.profiles = self._load_profiles()
        self.current_profile_name = DEFAULT_PROFILE_NAME
        self.device_name_to_id = {}
        self.current_device_id = None
        self.current_device_name = "未连接"
        self.wifi_ip_to_name = {}

        # --- 初始化后端控制器 ---
        self.adb_path = find_adb() or "adb"
        self.swipe_controller = HumanSwipeController(self.adb_path)
        self.click_controller = AdbController(self.adb_path)

        self.p1_detector = ImageDetector(IMAGE_FOLDER_SWIPER)
        self.runner = SwipeRunner(self.swipe_controller, self.p1_detector)
        self.p1_detector.start()

        self.hunter = ImageHunter(self.click_controller)

        # --- 创建UI (全新布局) ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)

        self._create_left_column()
        self._create_right_column()

        self.main_layout.setStretch(0, 2)
        self.main_layout.setStretch(1, 3)

        self._apply_stylesheet()
        self._connect_signals()

        # --- 初始化加载 ---
        self._update_profile_chooser()
        self.profile_chooser.setCurrentText(self.current_profile_name)
        self._load_profile(self.current_profile_name)
        QTimer.singleShot(100, self.refresh_devices)

    # --- UI 创建 (新布局) ---
    def _create_left_column(self):
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)

        theme_layout = QHBoxLayout()
        self.theme_btn = QPushButton("☀️ 白天模式")
        theme_layout.addStretch(1)
        theme_layout.addWidget(self.theme_btn)
        layout.addLayout(theme_layout)

        profile_group = QGroupBox("📂 场景配置")
        profile_layout = QVBoxLayout()
        self.profile_chooser = QComboBox()
        btn_layout = QGridLayout()
        self.save_profile_btn = QPushButton("💾 保存")
        self.add_profile_btn = QPushButton("➕ 新增")
        self.del_profile_btn = QPushButton("❌ 删除")
        self.load_profile_btn = QPushButton("📂 调取")
        btn_layout.addWidget(self.save_profile_btn, 0, 0)
        btn_layout.addWidget(self.add_profile_btn, 0, 1)
        btn_layout.addWidget(self.del_profile_btn, 1, 0)
        btn_layout.addWidget(self.load_profile_btn, 1, 1)
        profile_layout.addWidget(QLabel("选择配置文件:"))
        profile_layout.addWidget(self.profile_chooser)
        profile_layout.addLayout(btn_layout)
        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)

        status_group = QGroupBox("📊 状态监控")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("状态：已停止")
        self.countdown_label = QLabel("下次循环倒计时：-- 秒")
        self.image_status_label = QLabel("P1图像检测：未开启")
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.countdown_label)
        status_layout.addWidget(self.image_status_label)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        log_group = QGroupBox("📜 共享日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.clear_log_btn = QPushButton("🗑️ 清除日志")
        log_layout.addWidget(self.log_text)
        log_layout.addWidget(self.clear_log_btn)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.setStretch(0, 0)
        layout.setStretch(1, 0)
        layout.setStretch(2, 0)
        layout.setStretch(3, 1)

        self.main_layout.addWidget(left_widget)

    def _create_right_column(self):
        right_widget = QWidget()
        layout = QVBoxLayout(right_widget)

        device_group = QGroupBox("📱 设备控制")
        device_layout = QVBoxLayout()
        self.device_chooser = QComboBox()
        self.scrcpy_buttons_layout = QVBoxLayout()
        device_actions_layout = QGridLayout()
        self.refresh_devices_btn = QPushButton("🔄 刷新")
        self.wifi_connect_btn = QPushButton("📶 一键WIFI连接")
        self.kill_server_btn = QPushButton("💀 清理ADB")
        device_actions_layout.addWidget(self.refresh_devices_btn, 0, 0)
        device_actions_layout.addWidget(self.wifi_connect_btn, 0, 1)
        device_actions_layout.addWidget(self.kill_server_btn, 1, 0, 1, 2)
        device_layout.addWidget(QLabel("选择控制目标:"))
        device_layout.addWidget(self.device_chooser)
        device_layout.addLayout(self.scrcpy_buttons_layout)
        device_layout.addLayout(device_actions_layout)
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        swiper_card = QGroupBox("▶ 滑动器 (Swiper)")
        swiper_layout = QVBoxLayout()
        self.swiper_start_btn = QPushButton("▶ 开始循环 (P1)")
        self.swiper_start_btn.setObjectName("StartButton")
        self.swiper_stop_btn = QPushButton("■ 停止循环 (P1)")
        self.swiper_stop_btn.setObjectName("StopButton")
        self.swiper_stop_btn.setEnabled(False)
        self.swiper_settings_btn = QPushButton("⚙️ 设置")
        swiper_layout.addWidget(self.swiper_start_btn)
        swiper_layout.addWidget(self.swiper_stop_btn)
        swiper_layout.addWidget(self.swiper_settings_btn)
        swiper_card.setLayout(swiper_layout)
        layout.addWidget(swiper_card)

        hunter_card = QGroupBox("🎯 狩猎器 (Hunter)")
        hunter_layout = QVBoxLayout()
        self.hunter_start_btn = QPushButton("▶ 启动狩猎 (P2)")
        self.hunter_start_btn.setObjectName("StartButton")
        self.hunter_stop_btn = QPushButton("■ 停止狩猎 (P2)")
        self.hunter_stop_btn.setObjectName("StopButton")
        self.hunter_stop_btn.setEnabled(False)
        self.hunter_settings_btn = QPushButton("⚙️ 设置")
        hunter_layout.addWidget(self.hunter_start_btn)
        hunter_layout.addWidget(self.hunter_stop_btn)
        hunter_layout.addWidget(self.hunter_settings_btn)
        hunter_card.setLayout(hunter_layout)
        layout.addWidget(hunter_card)

        layout.addStretch(1)
        self.main_layout.addWidget(right_widget)

    def _connect_signals(self):
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.refresh_devices_btn.clicked.connect(self.refresh_devices)
        self.kill_server_btn.clicked.connect(self.kill_server)
        self.device_chooser.currentTextChanged.connect(self._on_device_switch)
        self.wifi_connect_btn.clicked.connect(self._wifi_connect)
        self.clear_log_btn.clicked.connect(self.log_text.clear)
        self.profile_chooser.currentTextChanged.connect(self._on_profile_switch)
        self.save_profile_btn.clicked.connect(self._save_current_profile)
        self.add_profile_btn.clicked.connect(self._add_new_profile)
        self.del_profile_btn.clicked.connect(self._delete_profile)
        self.load_profile_btn.clicked.connect(self._load_profiles_from_file_dialog)
        self.swiper_start_btn.clicked.connect(self.start_runner)
        self.swiper_stop_btn.clicked.connect(self.runner.stop)
        self.swiper_settings_btn.clicked.connect(self.open_swiper_settings)
        self.hunter_start_btn.clicked.connect(self.start_hunter)
        self.hunter_stop_btn.clicked.connect(self.hunter.stop)
        self.hunter_settings_btn.clicked.connect(self.open_hunter_settings)
        self.runner.log_message.connect(self.log)
        self.runner.status_updated.connect(self.update_status)
        self.runner.countdown_updated.connect(self.update_countdown)
        self.runner.started.connect(self._on_runner_started)
        self.runner.stopped.connect(self._on_runner_stopped)
        self.hunter.log_message.connect(self.log)
        self.hunter.started.connect(self._on_hunter_started)
        self.hunter.stopped.connect(self._on_hunter_stopped)
        self.p1_detector.status_updated.connect(self._on_image_status)
        self.p1_detector.interrupt_requested.connect(self.runner.interrupt_countdown)

    def log(self, text: str):
        self.log_text.append(f"{time.strftime('%H:%M:%S')} — {text}")

    def update_status(self, text: str):
        self.status_label.setText(text)

    def update_countdown(self, text: str):
        self.countdown_label.setText(text)

    def refresh_devices(self):
        devices = get_connected_devices(self.adb_path)
        self.log(f"已检测到 {len(devices)} 个设备。")

        connected_ips = {dev for dev in devices if ":" in dev}
        self.wifi_ip_to_name = {
            ip: name for ip, name in self.wifi_ip_to_name.items() if ip in connected_ips
        }

        new_device_name_to_id = {}
        for dev in devices:
            display_name = ""
            if dev in self.wifi_ip_to_name:
                display_name = f"{self.wifi_ip_to_name[dev]} (WIFI)"
            else:
                display_name = ID_TO_NAME.get(dev, f"未知 {dev}")

            new_device_name_to_id[display_name] = dev

        self.device_name_to_id = new_device_name_to_id

        for i in reversed(range(self.scrcpy_buttons_layout.count())):
            self.scrcpy_buttons_layout.itemAt(i).widget().setParent(None)

        for name, dev_id in self.device_name_to_id.items():
            btn_text = f"开 {name}"
            btn = QPushButton(btn_text)
            btn.clicked.connect(
                lambda _, did=dev_id, dname=name: self.open_device(did, dname)
            )
            self.scrcpy_buttons_layout.addWidget(btn)

        self.device_chooser.blockSignals(True)
        self.device_chooser.clear()
        if self.device_name_to_id:
            self.device_chooser.addItems(self.device_name_to_id.keys())
            if self.current_device_name in self.device_name_to_id:
                self.device_chooser.setCurrentText(self.current_device_name)
            else:
                self.device_chooser.setCurrentIndex(0)
        else:
            self.device_chooser.addItem("未连接")
        self.device_chooser.blockSignals(False)
        self._on_device_switch(self.device_chooser.currentText())

    def _on_device_switch(self, device_name: str):
        if not device_name or device_name == "未连接":
            self.current_device_id, self.current_device_name = None, "未连接"
            self.swipe_controller.device, self.click_controller.device_id = None, None
            self.hunter.target_window_title = ""
            self.log("所有控制器已重置为'未连接'")
            return

        self.current_device_name = device_name
        self.current_device_id = self.device_name_to_id.get(device_name)
        if self.current_device_id:
            self.runner.stop()
            self.hunter.stop()
            try:
                self.swipe_controller.device = self.current_device_id
                self.swipe_controller.update_device_size()
                self.log(
                    f"[滑动器] 已切换到: {device_name} ({self.swipe_controller.width}x{self.swipe_controller.height})"
                )
                self.click_controller.set_device(self.current_device_id)
                self.log(
                    f"[狩猎器] 已切换到: {device_name} ({self.click_controller.width}x{self.click_controller.height})"
                )
                self._on_image_detection_toggle()
            except Exception as e:
                self.log(f"切换设备时出错: {e}")

    def open_device(self, device_id: str, display_name: str):
        if not Path(SCRCPY_PATH).exists():
            self.log(f"错误: Scrcpy 路径不存在: {SCRCPY_PATH}")
            QMessageBox.critical(self, "错误", f"Scrcpy路径未找到:\n{SCRCPY_PATH}")
            return

        cmd = [SCRCPY_PATH, "-S", "-s", device_id, "--window-title", display_name]
        self.log(f"正在打开设备 {display_name}...")
        subprocess.Popen(
            cmd, creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
        )

    def kill_server(self):
        self.log("正在执行 adb kill-server...")
        self.runner.stop()
        self.hunter.stop()
        try:
            p = run_adb(self.adb_path, ["kill-server"])
            if p.returncode == 0:
                self.log("✓ ADB 进程已清除。")
            else:
                self.log(f"警告：清除进程失败: {p.stderr.strip()}")
            self.refresh_devices()
        except Exception as e:
            self.log(f"清除进程操作异常: {e}")

    def _get_default_swiper_config(self):
        return {
            "start_x": 0.5,
            "start_y": 0.85,
            "end_x": 0.5,
            "end_y": 0.45,
            "duration_min": 400,
            "duration_max": 500,
            "jitter": 2,
            "steps_min": 25,
            "steps_max": 35,
            "coord_offset": 1.0,
            "interval_min": 4.0,
            "interval_max": 10.0,
            "detection_enabled": False,
            "p1_start_condition_enabled": False,
        }

    def _get_default_hunter_config(self):
        return {
            "min_s": 5.0,
            "max_s": 10.0,
            "conf": 0.8,
            "x_min": 0.3,
            "x_max": 0.7,
            "y_min": 0.3,
            "y_max": 0.7,
        }

    def _load_profiles(self):
        if CONFIG_FILE_COMBINED.exists():
            try:
                with open(CONFIG_FILE_COMBINED, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return {
            DEFAULT_PROFILE_NAME: {
                "swiper": self._get_default_swiper_config(),
                "hunter": self._get_default_hunter_config(),
            }
        }

    def _save_profiles(self):
        try:
            BASE_CONFIG_FOLDER.mkdir(exist_ok=True)
            with open(CONFIG_FILE_COMBINED, "w", encoding="utf-8") as f:
                json.dump(self.profiles, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"保存配置文件失败: {e}")

    def _update_profile_chooser(self):
        self.profile_chooser.blockSignals(True)
        self.profile_chooser.clear()
        self.profile_chooser.addItems(self.profiles.keys())
        self.profile_chooser.blockSignals(False)

    def _on_profile_switch(self, name):
        if name and name in self.profiles:
            self.runner.stop()
            self.hunter.stop()
            self._load_profile(name)

    def _load_profile(self, name):
        if name not in self.profiles:
            return
        self.current_profile_name = name
        if "swiper" not in self.profiles[name]:
            self.profiles[name]["swiper"] = self._get_default_swiper_config()
        if "hunter" not in self.profiles[name]:
            self.profiles[name]["hunter"] = self._get_default_hunter_config()
        self.log(f"✓ 已加载配置: '{name}'")
        self._on_image_detection_toggle()

    def _save_current_profile(self):
        if not self.current_profile_name:
            return
        self._save_profiles()
        self.log(f"✓ 配置 '{self.current_profile_name}' 已保存。")
        QMessageBox.information(
            self, "成功", f"配置 '{self.current_profile_name}' 已保存。"
        )

    def _add_new_profile(self):
        text, ok = QInputDialog.getText(self, "新增配置", "请输入新配置的名称:")
        if ok and text:
            if text in self.profiles:
                QMessageBox.warning(self, "错误", f"配置名称 '{text}' 已存在。")
            else:
                self.profiles[text] = json.loads(
                    json.dumps(self.profiles[self.current_profile_name])
                )
                self._update_profile_chooser()
                self.profile_chooser.setCurrentText(text)
                self._save_profiles()
                self.log(f"✓ 新增配置: '{text}'")

    def _delete_profile(self):
        name = self.current_profile_name
        if name == DEFAULT_PROFILE_NAME:
            QMessageBox.warning(self, "警告", "无法删除默认配置。")
            return
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除配置 '{name}' 吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self.profiles[name]
            self._update_profile_chooser()
            self.profile_chooser.setCurrentText(DEFAULT_PROFILE_NAME)
            self._save_profiles()
            self.log(f"✓ 配置 '{name}' 已删除。")

    def _load_profiles_from_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", str(BASE_CONFIG_FOLDER), "JSON Files (*.json)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    new_profiles = json.load(f)
                if not isinstance(new_profiles, dict) or not all(
                    "swiper" in v and "hunter" in v for v in new_profiles.values()
                ):
                    raise ValueError("文件格式不正确")
                self.profiles = new_profiles
                self._update_profile_chooser()
                self.profile_chooser.setCurrentIndex(0)
                self._save_profiles()
                self.log(
                    f"✓ 成功从 '{Path(path).name}' 加载了 {len(new_profiles)} 个配置。"
                )
            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"无法加载或解析文件: {e}")

    def _on_runner_started(self):
        self.swiper_start_btn.setEnabled(False)
        self.swiper_stop_btn.setEnabled(True)
        self.device_chooser.setEnabled(False)
        self.profile_chooser.setEnabled(False)

    def _on_runner_stopped(self):
        self.swiper_start_btn.setEnabled(True)
        self.swiper_stop_btn.setEnabled(False)
        if not (self.hunter._thread and self.hunter._thread.is_alive()):
            self.device_chooser.setEnabled(True)
            self.profile_chooser.setEnabled(True)

    def _on_hunter_started(self):
        self.hunter_start_btn.setEnabled(False)
        self.hunter_stop_btn.setEnabled(True)
        self.device_chooser.setEnabled(False)
        self.profile_chooser.setEnabled(False)

    def _on_hunter_stopped(self):
        self.hunter_start_btn.setEnabled(True)
        self.hunter_stop_btn.setEnabled(False)
        if not self.runner._running:
            self.device_chooser.setEnabled(True)
            self.profile_chooser.setEnabled(True)

    def start_runner(self):
        if not self.current_device_id:
            QMessageBox.critical(self, "错误", "请先选择一个目标设备。")
            return
        self.runner.start(self.profiles[self.current_profile_name].get("swiper"))

    def start_hunter(self):
        if not self.current_device_id:
            QMessageBox.critical(self, "错误", "请先选择一个目标设备。")
            return
        self.hunter.start(
            self.profiles[self.current_profile_name].get("hunter"),
            self.current_device_name,
        )

    def open_swiper_settings(self):
        config = self.profiles[self.current_profile_name].get(
            "swiper", self._get_default_swiper_config()
        )
        dialog = SwiperSettingsDialog(config, self)
        if dialog.exec():
            self.profiles[self.current_profile_name]["swiper"] = dialog.get_config()
            self._on_image_detection_toggle()
            self.log("滑动器参数已更新。建议点击保存按钮持久化。")

    def open_hunter_settings(self):
        config = self.profiles[self.current_profile_name].get(
            "hunter", self._get_default_hunter_config()
        )
        dialog = HunterSettingsDialog(config, self)
        if dialog.exec():
            self.profiles[self.current_profile_name]["hunter"] = dialog.get_config()
            self.log("狩猎器参数已更新。建议点击保存按钮持久化。")

    def _on_image_detection_toggle(self):
        if self.current_profile_name not in self.profiles:
            return
        enabled = self.profiles[self.current_profile_name]["swiper"].get(
            "detection_enabled", False
        )
        if enabled and self.current_device_name != "未连接":
            self.p1_detector.enable(self.current_device_name)
            self.log("[滑动器] P1图像检测已启用。")
        else:
            self.p1_detector.disable()
            self.log("[滑动器] P1图像检测已禁用。")
        self._on_image_status(found=False)

    def _on_image_status(self, found: bool):
        if not self.p1_detector._running.is_set():
            self.image_status_label.setText("P1图像检测：已禁用")
            self.image_status_label.setStyleSheet("color: #888;")
            return
        self.image_status_label.setText(
            f"P1图像检测：{'已发现目标' if found else '未检测到目标'}"
        )
        self.image_status_label.setStyleSheet(
            f"color: {'#4CAF50' if found else '#F44336'};"
        )

    def _wifi_connect(self):
        if not self.current_device_id or ":" in self.current_device_id:
            QMessageBox.warning(
                self, "操作无效", "请先在设备列表中选择一个通过USB连接的设备。"
            )
            return

        self.log(f"开始为设备 {self.current_device_name} 启动WIFI连接...")
        tcpip_result = run_adb(
            self.adb_path, ["-s", self.current_device_id, "tcpip", "5555"], timeout=5.0
        )
        if "restarting in TCP mode" not in tcpip_result.stdout:
            QMessageBox.critical(self, "错误", "开启TCP/IP模式失败，请检查设备连接。")
            return

        self.log("TCP/IP模式已开启，等待设备ADB服务重启...")

        device_ip = None
        for attempt in range(10):
            ip_result = run_adb(
                self.adb_path,
                ["-s", self.current_device_id, "shell", "ip", "addr", "show", "wlan0"],
                timeout=2.0,
            )
            match = re.search(
                r"inet (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", ip_result.stdout
            )
            if match:
                device_ip = match.group(1)
                self.log(f"成功获取设备IP地址: {device_ip} (在第 {attempt + 1} 次尝试)")
                break
            time.sleep(0.5)

        if not device_ip:
            self.log("错误: 无法获取设备IP地址。请确保设备已连接到WIFI。")
            QMessageBox.critical(
                self,
                "错误",
                "无法获取设备IP地址。\n请确保手机和电脑连接到同一个WIFI网络。",
            )
            return

        wifi_device_id = f"{device_ip}:5555"
        clean_name = self.current_device_name.replace(" (WIFI)", "")
        self.wifi_ip_to_name[wifi_device_id] = clean_name
        self.log(f"已记录WIFI映射：'{wifi_device_id}' -> '{clean_name}'")

        connect_result = run_adb(
            self.adb_path, ["connect", wifi_device_id], timeout=5.0
        )
        if (
            "connected to" in connect_result.stdout
            or "already connected" in connect_result.stdout
        ):
            QMessageBox.information(
                self,
                "成功",
                f"设备WIFI连接成功！\nIP: {wifi_device_id}\n现在可以拔掉USB数据线了。",
            )
            self.refresh_devices()
        else:
            del self.wifi_ip_to_name[wifi_device_id]
            QMessageBox.critical(
                self,
                "连接失败",
                f"连接到 {wifi_device_id} 失败。\n请重试或检查网络设置。",
            )

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "退出",
            "确定要退出吗？\n(将自动保存当前配置)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.runner.stop()
            self.hunter.stop()
            self._save_current_profile()
            self.p1_detector.stop()
            event.accept()
        else:
            event.ignore()

    def _toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        if self.is_dark_theme:
            self.setStyleSheet(self.QSS_DARK)
            self.theme_btn.setText("☀️ 白天模式")
        else:
            self.setStyleSheet(self.QSS_LIGHT)
            self.theme_btn.setText("🌙 暗夜模式")

    def _apply_stylesheet(self):
        self.setStyleSheet(self.QSS_DARK)

    # ==================== QSS样式表修改处 ====================
    def _define_stylesheets(self):
        common_styles = """
            QGroupBox { 
                border-radius: 8px; margin-top: 1ex; font-weight: bold; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; subcontrol-position: top left; 
                padding: 0 5px; border-radius: 4px; 
            }
            QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox { 
                border-radius: 4px; padding: 4px; 
            }
            QComboBox::drop-down { border: none; }
            QLabel { background-color: transparent; }
        """
        self.QSS_DARK = f"""
            QWidget {{ 
                background-color: #2E2E2E; color: #F0F0F0; 
                font-family: "Segoe UI", "Microsoft YaHei"; font-size: 10pt; 
            }}
            {common_styles}
            QGroupBox {{ border: 1px solid #555; }}
            QGroupBox::title {{ background-color: #2E2E2E; }}
            QPushButton {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #555, stop:1 #4A4A4A);
                border: 1px solid #666;
                border-bottom: 3px solid #333;
                padding: 6px 12px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #5A5A5A; }}
            QPushButton:pressed {{
                background-color: #3D3D3D;
                border-style: inset;
                padding-top: 8px;
            }}
            QPushButton:disabled {{ background-color: #404040; color: #888; border-bottom: 3px solid #282828;}}

            QPushButton#StartButton {{ background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34c759, stop:1 #28a745); border-bottom-color: #1D7733; color: white; }}
            QPushButton#StartButton:hover {{ background-color: #30d55b; }}
            QPushButton#StartButton:pressed {{ background-color: #218838; border-style: inset; padding-top: 8px; }}
            
            QPushButton#StopButton {{ background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff453a, stop:1 #dc3545); border-bottom-color: #A92834; color: white; }}
            QPushButton#StopButton:hover {{ background-color: #ff5b52; }}
            QPushButton#StopButton:pressed {{ background-color: #c82333; border-style: inset; padding-top: 8px; }}

            QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background-color: #252525; border: 1px solid #555; }}
        """
        self.QSS_LIGHT = f"""
            QWidget {{ 
                background-color: #F0F2F5; color: #1c1c1e; 
                font-family: "Segoe UI", "Microsoft YaHei"; font-size: 10pt; 
            }}
            {common_styles}
            QGroupBox {{ border: 1px solid #D1D1D6; }}
            QGroupBox::title {{ background-color: #F0F2F5; }}
            QPushButton {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #F0F0F0);
                border: 1px solid #C6C6C8;
                border-bottom: 3px solid #BDBDBD;
                padding: 6px 12px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #E8E8E8; }}
            QPushButton:pressed {{
                background-color: #DCDCDC;
                border-style: inset;
                padding-top: 8px;
            }}
            QPushButton:disabled {{ background-color: #EAEAEA; color: #AAAAAA; border-bottom: 3px solid #CECECE; }}

            QPushButton#StartButton {{ background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34c759, stop:1 #28a745); border-bottom-color: #1D7733; color: white; }}
            QPushButton#StartButton:hover {{ background-color: #30d55b; }}
            QPushButton#StartButton:pressed {{ background-color: #218838; border-style: inset; padding-top: 8px; }}
            
            QPushButton#StopButton {{ background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff453a, stop:1 #dc3545); border-bottom-color: #A92834; color: white; }}
            QPushButton#StopButton:hover {{ background-color: #ff5b52; }}
            QPushButton#StopButton:pressed {{ background-color: #c82333; border-style: inset; padding-top: 8px; }}
            
            QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background-color: #FFFFFF; border: 1px solid #C6C6C8; }}
        """
