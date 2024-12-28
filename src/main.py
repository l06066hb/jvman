import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from loguru import logger

from ui.main_window import MainWindow
from utils.config_manager import ConfigManager
from utils.system_utils import check_admin_rights

def setup_logger():
    """配置日志系统"""
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    
    logger.add(
        os.path.join(log_path, "jvman_{time}.log"),
        rotation="500 MB",
        retention="10 days",
        level="INFO"
    )

def main():
    """主程序入口"""
    # 在开发环境中暂时跳过管理员权限检查
    # if not check_admin_rights():
    #     logger.error("程序需要管理员权限才能运行")
    #     return

    # 初始化配置
    config = ConfigManager()
    config.set('version', '1.0.3')
    
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 设置应用图标
    icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icon', 'app.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 创建主窗口
    window = MainWindow(config)
    window.show()
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == '__main__':
    setup_logger()
    logger.info("JDK管理工具启动")
    main() 