# ui/dialogs.py
# =======================================================================
#
#        全功能控制器 - 设置对话框模块
#
# =======================================================================
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QDialogButtonBox,
    QLabel,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
)

from config import IMAGE_FOLDER_SWIPER, IMAGE_FOLDER_SWIPER_GATE, IMAGE_FOLDER_HUNTER


class SettingsDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)

        self.layout = QVBoxLayout(self)
        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)

        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

    def _add_row(self, row, label_text, widget1, widget2=None):
        self.grid_layout.addWidget(QLabel(label_text), row, 0)
        self.grid_layout.addWidget(widget1, row, 1)
        if widget2:
            self.grid_layout.addWidget(widget2, row, 2)


class SwiperSettingsDialog(SettingsDialog):
    def __init__(self, config, parent=None):
        super().__init__("滑动器设置 (P1)", parent)
        self.config = config.copy()

        self.start_x = QDoubleSpinBox(decimals=3, maximum=1.0, singleStep=0.01)
        self.start_y = QDoubleSpinBox(decimals=3, maximum=1.0, singleStep=0.01)
        self.end_x = QDoubleSpinBox(decimals=3, maximum=1.0, singleStep=0.01)
        self.end_y = QDoubleSpinBox(decimals=3, maximum=1.0, singleStep=0.01)
        self.duration_min = QSpinBox(maximum=5000)
        self.duration_max = QSpinBox(maximum=5000)
        self.jitter = QSpinBox(maximum=100)
        self.steps_min = QSpinBox(minimum=5, maximum=100)
        self.steps_max = QSpinBox(minimum=5, maximum=100)
        self.coord_offset = QDoubleSpinBox(decimals=2, maximum=50.0, suffix=" %")
        self.interval_min = QDoubleSpinBox(decimals=2, maximum=300.0, suffix=" s")
        self.interval_max = QDoubleSpinBox(decimals=2, maximum=300.0, suffix=" s")
        self.detection_enabled = QCheckBox(
            f"启用P1加速 (扫描: {IMAGE_FOLDER_SWIPER.name})"
        )
        self.start_condition_enabled = QCheckBox(
            f"启用P1启动条件 (扫描: {IMAGE_FOLDER_SWIPER_GATE.name})"
        )

        self._add_row(0, "起点 (X/Y):", self.start_x, self.start_y)
        self._add_row(1, "终点 (X/Y):", self.end_x, self.end_y)
        self._add_row(
            2, "滑动时长 (最小/最大 ms):", self.duration_min, self.duration_max
        )
        self._add_row(3, "滑动精细度 (最小/最大):", self.steps_min, self.steps_max)
        self._add_row(4, "Jitter:", self.jitter)
        self._add_row(5, "坐标随机偏移:", self.coord_offset)
        self._add_row(
            6, "循环间隔 (最小/最大 s):", self.interval_min, self.interval_max
        )
        self.grid_layout.addWidget(self.detection_enabled, 7, 0, 1, 3)
        self.grid_layout.addWidget(self.start_condition_enabled, 8, 0, 1, 3)

        self.populate_fields()

    def populate_fields(self):
        self.start_x.setValue(self.config.get("start_x", 0.5))
        self.start_y.setValue(self.config.get("start_y", 0.85))
        self.end_x.setValue(self.config.get("end_x", 0.5))
        self.end_y.setValue(self.config.get("end_y", 0.45))
        self.duration_min.setValue(self.config.get("duration_min", 400))
        self.duration_max.setValue(self.config.get("duration_max", 500))
        self.jitter.setValue(self.config.get("jitter", 2))
        self.steps_min.setValue(self.config.get("steps_min", 25))
        self.steps_max.setValue(self.config.get("steps_max", 35))
        self.coord_offset.setValue(self.config.get("coord_offset", 1.0))
        self.interval_min.setValue(self.config.get("interval_min", 4.0))
        self.interval_max.setValue(self.config.get("interval_max", 10.0))
        self.detection_enabled.setChecked(self.config.get("detection_enabled", False))
        self.start_condition_enabled.setChecked(
            self.config.get("p1_start_condition_enabled", False)
        )

    def get_config(self):
        return {
            "start_x": self.start_x.value(),
            "start_y": self.start_y.value(),
            "end_x": self.end_x.value(),
            "end_y": self.end_y.value(),
            "duration_min": self.duration_min.value(),
            "duration_max": self.duration_max.value(),
            "jitter": self.jitter.value(),
            "steps_min": self.steps_min.value(),
            "steps_max": self.steps_max.value(),
            "coord_offset": self.coord_offset.value(),
            "interval_min": self.interval_min.value(),
            "interval_max": self.interval_max.value(),
            "detection_enabled": self.detection_enabled.isChecked(),
            "p1_start_condition_enabled": self.start_condition_enabled.isChecked(),
        }


class HunterSettingsDialog(SettingsDialog):
    def __init__(self, config, parent=None):
        super().__init__("狩猎器设置 (P2)", parent)
        self.config = config.copy()

        self.min_s = QDoubleSpinBox(decimals=2, maximum=300.0, suffix=" s")
        self.max_s = QDoubleSpinBox(decimals=2, maximum=300.0, suffix=" s")
        self.conf = QDoubleSpinBox(
            decimals=2, minimum=0.1, maximum=1.0, singleStep=0.05
        )
        self.x_min = QDoubleSpinBox(decimals=2, maximum=1.0)
        self.x_max = QDoubleSpinBox(decimals=2, maximum=1.0)
        self.y_min = QDoubleSpinBox(decimals=2, maximum=1.0)
        self.y_max = QDoubleSpinBox(decimals=2, maximum=1.0)

        self._add_row(0, "行动前等待 (最小/最大 s):", self.min_s, self.max_s)
        self._add_row(1, "图像相似度 (0.1-1.0):", self.conf)
        self._add_row(2, "点击范围 X (最小/最大 %):", self.x_min, self.x_max)
        self._add_row(3, "点击范围 Y (最小/最大 %):", self.y_min, self.y_max)
        self.grid_layout.addWidget(
            QLabel(f"目标文件夹: {IMAGE_FOLDER_HUNTER}"), 4, 0, 1, 3
        )

        self.populate_fields()

    def populate_fields(self):
        self.min_s.setValue(self.config.get("min_s", 5.0))
        self.max_s.setValue(self.config.get("max_s", 10.0))
        self.conf.setValue(self.config.get("conf", 0.8))
        self.x_min.setValue(self.config.get("x_min", 0.3))
        self.x_max.setValue(self.config.get("x_max", 0.7))
        self.y_min.setValue(self.config.get("y_min", 0.3))
        self.y_max.setValue(self.config.get("y_max", 0.7))

    def get_config(self):
        return {
            "min_s": self.min_s.value(),
            "max_s": self.max_s.value(),
            "conf": self.conf.value(),
            "x_min": self.x_min.value(),
            "x_max": self.x_max.value(),
            "y_min": self.y_min.value(),
            "y_max": self.y_max.value(),
        }
