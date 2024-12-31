import sys
import os
import logging
import traceback
import ctypes

# 添加项目根目录到 Python 路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的环境
    project_root = os.path.dirname(sys.executable)
else:
    # 如果是开发环境
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
# 添加src目录到Python路径
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 定义后备Logger类
class Logger:
    def __init__(self):
        self._logger = logging.getLogger('jvman')
        self._logger.setLevel(logging.DEBUG)  # 设置为DEBUG级别
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self._logger.addHandler(console_handler)
    
    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
    
    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)
    
    def exception(self, msg, *args, exc_info=True, **kwargs):
        self._logger.exception(msg, *args, exc_info=exc_info, **kwargs)
    
    def add(self, *args, **kwargs):
        pass  # 兼容 loguru 的 add 方法

# 导入必要的模块
try:
    from loguru import logger
except ImportError:
    logger = Logger()

# 记录Python路径
logger.debug(f"Python path: {sys.path}")
logger.debug(f"Current working directory: {os.getcwd()}")
logger.debug(f"Project root: {project_root}")

def show_error_message(message):
    """显示错误消息对话框"""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        if not QApplication.instance():
            app = QApplication([])
        QMessageBox.critical(None, "Error", message)
    except Exception as e:
        logger.exception("Failed to show error message box")
        print(f"Error: {message}")

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    from ui.main_window import MainWindow
    from utils.config_manager import ConfigManager
    from utils.platform_manager import platform_manager
    from utils.version_manager import version_manager
except Exception as e:
    error_msg = f"Failed to import required modules:\n{str(e)}\n{traceback.format_exc()}"
    logger.exception(error_msg)
    show_error_message(error_msg)
    sys.exit(1)

def setup_logging():
    """设置日志"""
    try:
        log_path = os.path.join(project_root, 'logs')
        os.makedirs(log_path, exist_ok=True)
        
        if isinstance(logger, Logger):
            # 如果是后备的 logging，添加文件处理器
            file_handler = logging.FileHandler(os.path.join(log_path, 'jvman.log'))
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger._logger.addHandler(file_handler)
        else:
            # 如果是 loguru
            logger.add(
                os.path.join(log_path, 'jvman.log'),
                rotation='1 MB',
                retention='7 days',
                level='DEBUG'  # 设置为DEBUG级别
            )
    except Exception as e:
        logger.exception("Failed to setup logging")

def get_icon_path(icon_name):
    """获取图标路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的环境
        base_path = sys._MEIPASS
    else:
        # 如果是开发环境
        base_path = project_root
    
    icon_path = os.path.join(base_path, 'resources', 'icons', icon_name)
    if not os.path.exists(icon_path):
        logger.warning(f"Icon not found at: {icon_path}")
        return None
    return icon_path

def is_admin():
    """检查是否具有管理员权限（跨平台）"""
    try:
        if platform_manager.is_windows:
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:
            # Unix系统（Linux/macOS）检查是否为root用户
            return os.geteuid() == 0
    except:
        return False

def run_as_admin():
    """以管理员权限重新启动程序（跨平台）"""
    try:
        if sys.argv[-1] != 'asadmin':
            script = os.path.abspath(sys.argv[0])
            
            if platform_manager.is_windows:
                # Windows使用ShellExecute
                params = ' '.join([script] + sys.argv[1:] + ['asadmin'])
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
                if int(ret) > 32:
                    sys.exit(0)
                else:
                    raise Exception("Failed to elevate privileges")
            else:
                # Unix系统（Linux/macOS）使用sudo
                if platform_manager.is_macos:
                    sudo_command = 'osascript -e "do shell script \\"sudo ' + sys.executable + ' ' + script + '\\" with administrator privileges"'
                else:  # Linux
                    sudo_command = f'pkexec {sys.executable} {script}'
                
                os.system(sudo_command)
                sys.exit(0)
    except Exception as e:
        logger.error(f"请求管理员权限失败: {str(e)}")
        return False
    return True

def main():
    """主函数"""
    try:
        # 检查管理员权限
        if platform_manager.requires_admin and not is_admin():
            run_as_admin()
            return

        # 设置日志
        setup_logging()
        logger.debug("Logging setup completed")
        
        # 初始化配置
        config = ConfigManager()
        logger.debug("Configuration initialized")
        
        # 设置平台管理器的配置
        platform_manager.set_config(config)
        
        # 获取并记录平台信息
        platform_info = platform_manager.get_platform_info()
        logger.info(f"系统信息: {platform_info}")
        
        # 检查包管理器
        if package_manager := platform_info.get('package_manager'):
            logger.info(f"检测到包管理器: {package_manager['name']}")
        
        # 创建应用
        app = QApplication(sys.argv)
        app.setApplicationName(version_manager.app_name)
        app.setApplicationVersion(version_manager.version)
        logger.debug("Application created")
        
        # 设置应用图标
        if icon_path := get_icon_path('app.ico'):
            app_icon = QIcon(icon_path)
            app.setWindowIcon(app_icon)
            logger.debug(f"Application icon set from: {icon_path}")
        
        # 创建主窗口
        window = MainWindow(config)
        window.show()
        logger.debug("Main window created and shown")
        
        # 运行应用
        return app.exec()
    except Exception as e:
        error_msg = f"Application failed to start:\n{str(e)}\n{traceback.format_exc()}"
        logger.exception(error_msg)
        show_error_message(error_msg)
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        error_msg = f"Unhandled exception in main:\n{str(e)}\n{traceback.format_exc()}"
        logger.exception(error_msg)
        show_error_message(error_msg)
        sys.exit(1) 