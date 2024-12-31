import os
import platform
import subprocess
from loguru import logger

class PlatformManager:
    """平台管理器，处理平台特定的功能和配置"""
    
    def __init__(self):
        self.system = platform.system()
        self.is_windows = self.system == 'Windows'
        self.is_linux = self.system == 'Linux'
        self.is_macos = self.system == 'Darwin'
        self.shell = self._detect_shell()
        self.config = None  # 将在 set_config 中设置
        self.requires_admin = self.is_windows
        
    def set_config(self, config):
        """设置配置对象"""
        self.config = config
        
    def _detect_shell(self):
        """检测当前使用的shell"""
        if self.is_windows:
            return 'cmd'
        
        # 如果配置了自定义 shell，优先使用配置的值
        if self.config and self.config.get('shell_type') != 'auto':
            return self.config.get('shell_type')
        
        shell = os.environ.get('SHELL', '')
        if not shell:
            return 'unknown'
            
        shell_name = os.path.basename(shell).lower()
        if 'zsh' in shell_name:
            return 'zsh'
        elif 'bash' in shell_name:
            return 'bash'
        elif 'fish' in shell_name:
            return 'fish'
        return shell_name
        
    def get_shell_config_file(self):
        """获取shell配置文件路径"""
        if self.is_windows:
            return None
            
        # 如果配置了自定义配置文件路径，优先使用配置的值
        if self.config and self.config.get('shell_config_path'):
            return self.config.get('shell_config_path')
            
        home = os.path.expanduser('~')
        if self.shell == 'zsh':
            return os.path.join(home, '.zshrc')
        elif self.shell == 'bash':
            # 优先检查 .bash_profile
            bash_profile = os.path.join(home, '.bash_profile')
            if os.path.exists(bash_profile):
                return bash_profile
            return os.path.join(home, '.bashrc')
        elif self.shell == 'fish':
            return os.path.join(home, '.config/fish/config.fish')
        return os.path.join(home, '.profile')
        
    def get_shell_reload_command(self):
        """获取重新加载shell配置的命令"""
        if self.is_windows:
            return None
            
        config_file = self.get_shell_config_file()
        if not config_file:
            return None
            
        if self.shell == 'fish':
            return f'source {config_file}'
        return f'. {config_file}'
        
    def get_package_manager(self):
        """获取包管理器信息"""
        if self.is_macos:
            if self._check_command('brew'):
                return {
                    'name': 'homebrew',
                    'install_cmd': 'brew install openjdk@{version}',
                    'uninstall_cmd': 'brew uninstall openjdk@{version}',
                    'list_cmd': 'brew list | grep openjdk'
                }
        elif self.is_linux:
            if self._check_command('apt'):
                return {
                    'name': 'apt',
                    'install_cmd': 'sudo apt install openjdk-{version}-jdk',
                    'uninstall_cmd': 'sudo apt remove openjdk-{version}-jdk',
                    'list_cmd': 'apt list --installed | grep openjdk'
                }
            elif self._check_command('yum'):
                return {
                    'name': 'yum',
                    'install_cmd': 'sudo yum install java-{version}-openjdk',
                    'uninstall_cmd': 'sudo yum remove java-{version}-openjdk',
                    'list_cmd': 'yum list installed | grep java-.*-openjdk'
                }
        return None
        
    def _check_command(self, cmd):
        """检查命令是否可用"""
        try:
            subprocess.run(['which', cmd], capture_output=True, text=True)
            return True
        except:
            return False
            
    def get_platform_info(self):
        """获取平台信息"""
        info = {
            'system': self.system,
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'shell': self.shell,
            'shell_config': self.get_shell_config_file(),
            'is_admin': self.check_admin_rights(),
            'package_manager': self.get_package_manager()
        }
        return info
        
    def check_admin_rights(self):
        """检查是否有管理员权限"""
        try:
            if self.is_windows:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except:
            return False
            
    def get_platform_requirements(self):
        """获取平台特定的要求信息"""
        if self.is_windows:
            return {
                'admin_required': True,
                'message': '需要管理员权限来修改系统环境变量和创建符号链接。'
            }
        else:
            return {
                'admin_required': True,
                'message': f'需要 sudo 权限来修改系统环境变量。配置文件位置：{self.get_shell_config_file()}'
            }
            
    def get_error_message(self, error_type, **kwargs):
        """获取平台特定的错误消息"""
        messages = {
            'admin_rights': {
                'windows': '请以管理员身份运行程序以修改系统环境变量。',
                'unix': '请使用 sudo 运行程序或手动修改环境变量配置文件。'
            },
            'symlink_failed': {
                'windows': '创建符号链接失败。Windows 10以下版本需要管理员权限。',
                'unix': '创建符号链接失败，请检查权限和路径是否正确。'
            },
            'env_var_failed': {
                'windows': '修改系统环境变量失败，请确保有管理员权限。',
                'unix': f'修改环境变量失败，请手动编辑配置文件：{self.get_shell_config_file()}'
            }
        }
        
        platform_type = 'windows' if self.is_windows else 'unix'
        base_message = messages.get(error_type, {}).get(platform_type, '操作失败')
        
        if kwargs.get('detail'):
            return f"{base_message}\n详细信息：{kwargs['detail']}"
        return base_message
        
    def format_path(self, path):
        """格式化路径为平台特定的格式"""
        if self.is_windows:
            return path.replace('/', '\\')
        return path.replace('\\', '/')
        
    def get_java_executable(self):
        """获取Java可执行文件名"""
        return 'java.exe' if self.is_windows else 'java'
        
    def get_path_separator(self):
        """获取路径分隔符"""
        return ';' if self.is_windows else ':'

# 创建全局实例
platform_manager = PlatformManager() 