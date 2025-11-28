# main.py
# =======================================================================
#
#        全功能控制器 (模块化版本 v6.0) - 主程序入口
#
# =======================================================================
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import SwipeApp_PyQt

if __name__ == "__main__":
    """
    程序的主入口。
    它的唯一职责是创建并运行Qt应用程序和主窗口。
    """
    app = QApplication(sys.argv)
    window = SwipeApp_PyQt()
    window.show()
    sys.exit(app.exec())
