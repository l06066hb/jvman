import os
import sys
import ctypes
import platform
import subprocess
from abc import ABC, abstractmethod
from loguru import logger
from .platform_manager import platform_manager
import winreg
import win32gui
import win32con

class SystemManager(ABC):
    """系统管理抽象基类"""
    
    @abstractmethod
    def check_admin_rights(self):
        """检查是否具有管理员权限"""
        pass
        
    @abstractmethod
    def create_symlink(self, source_path, target_path):
        """创建符号链接"""
        pass
        
    @abstractmethod
    def set_environment_variable(self, name, value):
        """设置系统环境变量"""
        pass
        
    @abstractmethod
    def get_environment_variable(self, name):
        """获取系统环境变量值"""
        pass
        
    @abstractmethod
    def update_path_variable(self, new_path):
        """更新PATH环境变量"""
        pass

class WindowsManager(SystemManager):
    """Windows系统管理器"""
    
    def check_admin_rights(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
            
    def create_symlink(self, source_path, target_path):
        """创建符号链接"""
        try:
            if os.path.exists(target_path):
                os.remove(target_path)
            
            # Windows 上使用 junction
            if platform.system() == 'Windows':
                # 使用 mklink /J 创建目录联接
                result = os.system(f'mklink /J "{target_path}" "{source_path}"')
                return result == 0
            else:
                # 其他系统使用 symlink
                os.symlink(source_path, target_path, target_is_directory=True)
                return True
        except Exception as e:
            logger.error(f"创建符号链接失败: {str(e)}")
            return False
            
    def set_environment_variable(self, name, value):
        try:
            # 检查权限
            if not self.check_admin_rights():
                error_msg = platform_manager.get_error_message('admin_rights')
                logger.error(error_msg)
                return False

            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r'System\CurrentControlSet\Control\Session Manager\Environment',
                0,
                winreg.KEY_ALL_ACCESS
            )
            winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
            winreg.CloseKey(key)
            os.system('rundll32.exe user32.dll,UpdatePerUserSystemParameters')
            return True
        except Exception as e:
            logger.error(f"设置环境变量失败: {str(e)}")
            return False
            
    def get_environment_variable(self, name):
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r'System\CurrentControlSet\Control\Session Manager\Environment',
                0,
                winreg.KEY_READ
            )
            value, _ = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return value
        except Exception as e:
            logger.error(f"获取环境变量失败: {str(e)}")
            return None
            
    def update_path_variable(self, new_path):
        try:
            # 检查权限
            if not self.check_admin_rights():
                error_msg = platform_manager.get_error_message('admin_rights')
                logger.error(error_msg)
                return False

            current_path = self.get_environment_variable('Path')
            paths = current_path.split(';')
            paths = [p for p in paths if 'jdk' not in p.lower()]
            if new_path not in paths:
                paths.append(new_path)
            new_path_value = ';'.join(filter(None, paths))
            return self.set_environment_variable('Path', new_path_value)
        except Exception as e:
            logger.error(f"更新PATH环境变量失败: {str(e)}")
            return False

class UnixManager(SystemManager):
    """Unix系统管理器（Linux/macOS）"""
    
    def check_admin_rights(self):
        return platform_manager.check_admin_rights()
            
    def create_symlink(self, source_path, target_path):
        try:
            if os.path.exists(target_path):
                os.remove(target_path)
            source_path = platform_manager.format_path(source_path)
            target_path = platform_manager.format_path(target_path)
            os.symlink(source_path, target_path)
            return True
        except Exception as e:
            error_msg = platform_manager.get_error_message('symlink_failed', detail=str(e))
            logger.error(error_msg)
            return False
            
    def set_environment_variable(self, name, value):
        try:
            config_file = platform_manager.get_shell_config_file()
            if not config_file:
                raise Exception("无法确定shell配置文件位置")
            
            # 读取现有内容
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []
            
            # 根据不同shell生成导出命令
            if platform_manager.shell == 'fish':
                export_cmd = f'set -x {name} "{value}"\n'
                lines = [line for line in lines if not line.startswith(f'set -x {name} ')]
            else:
                export_cmd = f'export {name}="{value}"\n'
                lines = [line for line in lines if not line.startswith(f'export {name}=')]
            
            # 添加新的设置
            lines.append(export_cmd)
            
            # 写入文件
            with open(config_file, 'w') as f:
                f.writelines(lines)
            
            # 立即生效
            os.environ[name] = value
            
            # 提供重新加载命令
            reload_cmd = platform_manager.get_shell_reload_command()
            if reload_cmd:
                logger.info(f"请运行以下命令使环境变量生效：{reload_cmd}")
            
            return True
        except Exception as e:
            error_msg = platform_manager.get_error_message('env_var_failed', detail=str(e))
            logger.error(error_msg)
            return False
            
    def get_environment_variable(self, name):
        try:
            return os.environ.get(name)
        except Exception as e:
            logger.error(f"获取环境变量失败: {str(e)}")
            return None
            
    def update_path_variable(self, new_path):
        try:
            current_path = self.get_environment_variable('PATH')
            if current_path:
                separator = platform_manager.get_path_separator()
                paths = current_path.split(separator)
                paths = [p for p in paths if 'jdk' not in p.lower()]
                if new_path not in paths:
                    paths.append(new_path)
                new_path_value = separator.join(filter(None, paths))
                return self.set_environment_variable('PATH', new_path_value)
            return False
        except Exception as e:
            error_msg = platform_manager.get_error_message('env_var_failed', detail=str(e))
            logger.error(error_msg)
            return False

def get_system_manager():
    """获取对应平台的系统管理器"""
    system = platform.system()
    if system == 'Windows':
        return WindowsManager()
    elif system in ['Linux', 'Darwin']:
        return UnixManager()
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")

# 创建全局系统管理器实例
system_manager = get_system_manager()

# 为了保持向后兼容，提供全局函数
def check_admin_rights():
    return system_manager.check_admin_rights()

def create_symlink(source_path, target_path):
    return system_manager.create_symlink(source_path, target_path)

def set_environment_variable(name, value):
    return system_manager.set_environment_variable(name, value)

def get_environment_variable(name):
    return system_manager.get_environment_variable(name)

def update_path_variable(java_home_path):
    """更新 PATH 环境变量"""
    try:
        # 获取当前的 PATH 环境变量
        current_path = os.environ.get('PATH', '')
        paths = current_path.split(os.pathsep)
        
        # 移除所有包含 java 或 jdk 的路径
        paths = [p for p in paths if not any(x in p.lower() for x in ['java', 'jdk'])]
        
        # 添加新的 Java 路径（使用 %JAVA_HOME%\bin）
        paths.insert(0, '%JAVA_HOME%\\bin')
        
        # 合并并更新 PATH
        new_path = os.pathsep.join(paths)
        
        # 使用 winreg 更新系统环境变量
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment', 0, winreg.KEY_SET_VALUE | winreg.KEY_READ) as key:
            winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
            
        # 发送环境变量更改的广播消息
        win32gui.SendMessageTimeout(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment', win32con.SMTO_ABORTIFHUNG, 5000)
        
        return True
    except Exception as e:
        logger.error(f"更新 PATH 环境变量失败: {str(e)}")
        return False 