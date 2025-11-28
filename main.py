# main.py
# =======================================================================
#
#        全功能控制器 (模块化版本 v6.0) - 主程序入口
#
# =======================================================================
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import SwipeApp_PyQt

# --- ↓↓↓ 新增图标修复代码，解决Windows任务栏图标问题 ↓↓↓ ---
import ctypes

# 定义一个唯一的应用程序ID，格式可以自定义，只要不冲突即可
myappid = "lww3716.tools.controller.1.0"
# 调用Windows API，设置当前进程的AppUserModelID
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
# --- ↑↑↑ 新增代码结束 ↑↑↑ ---


if __name__ == "__main__":
    """
    程序的主入口。
    它的唯一职责是创建并运行Qt应用程序和主窗口。
    """
    app = QApplication(sys.argv)
    window = SwipeApp_PyQt()
    window.show()
    sys.exit(app.exec())
