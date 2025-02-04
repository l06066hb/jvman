import os
import sys
import ctypes
import platform
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def hide_console():
    """隐藏控制台窗口"""
    try:
        if platform.system() == "Windows":
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            user32 = ctypes.WinDLL("user32", use_last_error=True)

            # 获取当前进程的控制台窗口
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                # 隐藏窗口
                user32.ShowWindow(hwnd, 0)

                # 设置控制台模式
                handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
                if handle and handle != -1:
                    mode = ctypes.c_ulong()
                    kernel32.GetConsoleMode(handle, ctypes.byref(mode))
                    mode.value &= ~0x0002  # ENABLE_ECHO_INPUT
                    mode.value &= ~0x0004  # ENABLE_LINE_INPUT
                    kernel32.SetConsoleMode(handle, mode)
    except Exception:
        pass


def setup_subprocess():
    """设置子进程创建标志"""
    try:
        if platform.system() == "Windows":
            # 设置子进程创建标志
            subprocess.CREATE_NO_WINDOW = 0x08000000
            subprocess.DETACHED_PROCESS = 0x00000008

            # 修改 subprocess 模块的默认标志
            if hasattr(subprocess, "_subprocess"):
                subprocess._subprocess.CREATE_NO_WINDOW = 0x08000000
                subprocess._subprocess.DETACHED_PROCESS = 0x00000008

            # 设置默认的 startupinfo
            subprocess.STARTF_USESHOWWINDOW = 0x00000001

            # 修改 subprocess.Popen 的默认参数
            original_init = subprocess.Popen.__init__

            def new_init(self, *args, **kwargs):
                if "startupinfo" not in kwargs:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = 0  # SW_HIDE
                    kwargs["startupinfo"] = startupinfo
                if "creationflags" not in kwargs:
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                original_init(self, *args, **kwargs)

            subprocess.Popen.__init__ = new_init
    except Exception as e:
        logger.error(f"[setup_subprocess] 设置子进程创建标志失败: {str(e)}")
        pass


def setup_dpi_awareness():
    """设置DPI感知"""
    try:
        if platform.system() == "Windows":
            # 设置进程级别的DPI感知
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(
                    1
                )  # PROCESS_SYSTEM_DPI_AWARE
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def runtime_hook():
    """
    运行时钩子，用于处理资源文件路径
    """
    if getattr(sys, "frozen", False):
        # 运行在打包环境
        base_path = sys._MEIPASS
    else:
        # 运行在开发环境
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # 添加资源目录到 Python 路径
    resource_paths = [
        base_path,
        os.path.join(base_path, "src"),
        os.path.join(base_path, "resources"),
        os.path.join(base_path, "resources", "icons"),
        os.path.join(base_path, "resources", "tools"),
    ]

    for path in resource_paths:
        if path not in sys.path and os.path.exists(path):
            sys.path.append(path)
            logger.debug(f"Added to Python path: {path}")
        else:
            logger.warning(f"Path not found or already in sys.path: {path}")

    # 设置环境变量
    os.environ["JVMAN_ROOT"] = base_path  # 添加根目录环境变量
    os.environ["JVMAN_ICONS"] = os.path.join(
        base_path, "resources", "icons"
    )  # 添加图标目录环境变量
    os.environ["JVMAN_TOOLS"] = os.path.join(
        base_path, "resources", "tools"
    )  # 添加工具目录环境变量

    logger.debug(f"Environment variables set: JVMAN_ROOT={os.environ['JVMAN_ROOT']}")
    logger.debug(f"Environment variables set: JVMAN_ICONS={os.environ['JVMAN_ICONS']}")
    logger.debug(f"Environment variables set: JVMAN_TOOLS={os.environ['JVMAN_TOOLS']}")

    return base_path


if __name__ == "__main__":
    if platform.system() == "Windows":
        # 设置DPI感知
        setup_dpi_awareness()

        # 隐藏控制台窗口
        hide_console()

        # 设置子进程创建标志
        setup_subprocess()
