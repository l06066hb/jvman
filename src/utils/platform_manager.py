import os
import platform
import subprocess
import shutil
from loguru import logger
from utils.i18n_manager import i18n_manager

# 初始化翻译函数
_ = i18n_manager.get_text


class PlatformManager:
    """平台管理器，处理平台特定的功能和配置"""

    def __init__(self):
        self.system = platform.system()
        self.is_windows = self.system == "Windows"
        self.is_linux = self.system == "Linux"
        self.is_macos = self.system == "Darwin"
        self.config = None  # 将 config 的初始化移到前面
        self._arch = self._detect_arch()  # 添加架构检测
        self.shell = self._detect_shell()  # shell 检测移到最后
        self.requires_admin = self.is_windows

    def set_config(self, config):
        """设置配置对象"""
        self.config = config

    def _detect_shell(self):
        """检测当前使用的shell"""
        if self.is_windows:
            return "cmd"

        # 如果配置了自定义 shell，优先使用配置的值
        if self.config and self.config.get("shell_type") != "auto":
            return self.config.get("shell_type")

        shell = os.environ.get("SHELL", "")
        if not shell:
            return "unknown"

        shell_name = os.path.basename(shell).lower()
        if "zsh" in shell_name:
            return "zsh"
        elif "bash" in shell_name:
            return "bash"
        elif "fish" in shell_name:
            return "fish"
        return shell_name

    def get_shell_config_file(self):
        """获取shell配置文件路径"""
        if self.is_windows:
            return None

        # 不再使用配置中的自定义路径，而是使用标准路径
        home = os.path.expanduser("~")

        # 优先使用 .bash_profile（标准的环境变量配置文件）
        bash_profile = os.path.join(home, ".bash_profile")
        if os.path.exists(bash_profile):
            return bash_profile

        # 如果 .bash_profile 不存在，使用 .profile
        profile = os.path.join(home, ".profile")
        return profile

    def get_shell_reload_command(self):
        # """获取shell重新加载命令"""
        # if self.is_windows:
        #     return None

        # # 获取实际使用的配置文件
        # config_file = self.get_shell_config_file()
        # if config_file:
        #     return f"source {config_file}"
        return None

    def get_package_manager(self):
        """获取包管理器信息"""
        if self.is_macos:
            if self._check_command("brew"):
                return {
                    "name": "homebrew",
                    "install_cmd": "brew install openjdk@{version}",
                    "uninstall_cmd": "brew uninstall openjdk@{version}",
                    "list_cmd": "brew list | grep openjdk",
                }
        elif self.is_linux:
            if self._check_command("apt"):
                return {
                    "name": "apt",
                    "install_cmd": "sudo apt install openjdk-{version}-jdk",
                    "uninstall_cmd": "sudo apt remove openjdk-{version}-jdk",
                    "list_cmd": "apt list --installed | grep openjdk",
                }
            elif self._check_command("yum"):
                return {
                    "name": "yum",
                    "install_cmd": "sudo yum install java-{version}-openjdk",
                    "uninstall_cmd": "sudo yum remove java-{version}-openjdk",
                    "list_cmd": "yum list installed | grep java-.*-openjdk",
                }
        return None

    def _check_command(self, cmd):
        """检查命令是否可用"""
        try:
            subprocess.run(["which", cmd], capture_output=True, text=True)
            return True
        except:
            return False

    def get_platform_info(self):
        """获取平台信息"""
        info = {
            "system": self.system,
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "shell": self.shell,
            "shell_config": self.get_shell_config_file(),
            "is_admin": self.check_admin_rights(),
            "package_manager": self.get_package_manager(),
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
            return {"admin_required": True, "message": "需要管理员权限来修改系统环境变量和创建符号链接。"}
        else:
            return {
                "admin_required": True,
                "message": f"需要 sudo 权限来修改系统环境变量。配置文件位置：{self.get_shell_config_file()}",
            }

    def get_error_message(self, error_type, **kwargs):
        """获取平台特定的错误消息"""
        messages = {
            "admin_rights": {
                "windows": _("error.admin_rights.windows"),
                "unix": _("error.admin_rights.unix"),
            },
            "symlink_failed": {
                "windows": _("error.symlink_failed.windows"),
                "unix": _("error.symlink_failed.unix"),
            },
            "env_var_failed": {
                "windows": _("error.env_var_failed.windows"),
                "unix": _("error.env_var_failed.unix").format(
                    config_file=self.get_shell_config_file()
                ),
            },
        }

        platform_type = "windows" if self.is_windows else "unix"
        base_message = messages.get(error_type, {}).get(
            platform_type, _("error.unknown")
        )

        if kwargs.get("detail"):
            return _("error.with_detail").format(
                base_message=base_message, detail=kwargs["detail"]
            )
        return base_message

    def format_path(self, path):
        """格式化路径为平台特定的格式"""
        try:
            # 规范化路径分隔符
            normalized_path = os.path.normpath(path)

            # 根据平台转换分隔符
            if self.is_windows:
                return normalized_path.replace("/", "\\")
            return normalized_path.replace("\\", "/")
        except Exception as e:
            logger.error(f"路径格式化失败: {str(e)}")
            return path

    def normalize_path(self, path):
        """规范化路径（解析相对路径、环境变量等）"""
        try:
            # 展开环境变量
            expanded_path = os.path.expandvars(path)
            # 展开用户目录
            expanded_path = os.path.expanduser(expanded_path)
            # 转换为绝对路径
            abs_path = os.path.abspath(expanded_path)
            # 规范化路径分隔符
            return self.format_path(abs_path)
        except Exception as e:
            logger.error(f"路径规范化失败: {str(e)}")
            return path

    def is_same_path(self, path1, path2):
        """检查两个路径是否指向相同位置"""
        try:
            # 规范化两个路径
            norm_path1 = self.normalize_path(path1)
            norm_path2 = self.normalize_path(path2)

            # Windows下不区分大小写
            if self.is_windows:
                return os.path.normcase(norm_path1) == os.path.normcase(norm_path2)
            return norm_path1 == norm_path2
        except Exception as e:
            logger.error(f"路径比较失败: {str(e)}")
            return False

    def is_subpath(self, parent_path, child_path):
        """检查一个路径是否是另一个路径的子路径"""
        try:
            # 规范化路径
            parent = self.normalize_path(parent_path)
            child = self.normalize_path(child_path)

            # Windows下不区分大小写
            if self.is_windows:
                parent = os.path.normcase(parent)
                child = os.path.normcase(child)

            # 使用相对路径检查
            rel_path = os.path.relpath(child, parent)
            return not rel_path.startswith("..")
        except Exception as e:
            logger.error(f"子路径检查失败: {str(e)}")
            return False

    def ensure_dir_exists(self, path):
        """确保目录存在，如果不存在则创建"""
        try:
            normalized_path = self.normalize_path(path)
            if not os.path.exists(normalized_path):
                os.makedirs(normalized_path, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"创建目录失败: {str(e)}")
            return False

    def get_java_executable(self):
        """获取Java可执行文件名"""
        return "java.exe" if self.is_windows else "java"

    def get_path_separator(self):
        """获取路径分隔符"""
        return ";" if self.is_windows else ":"

    def get_env_var_commands(self, name, value):
        """获取设置环境变量的命令
        Args:
            name: 环境变量名
            value: 环境变量值
        Returns:
            list: 环境变量设置命令列表
        """
        if self.is_windows:
            return None

        # 根据不同的环境变量使用不同的设置方式
        if name == "JAVA_HOME":
            # JAVA_HOME 设置
            commands = [f'export JAVA_HOME="{value}"']
        elif name == "PATH":
            # PATH 设置，使用 JAVA_HOME 变量引用
            commands = ['export PATH="$JAVA_HOME/bin:$PATH"']
        elif name == "CLASSPATH":
            # CLASSPATH 设置，使用 JAVA_HOME 变量引用
            commands = [
                'export CLASSPATH=".:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar"'
            ]
        else:
            # 其他环境变量的常规设置
            commands = [f'export {name}="{value}"']

        return commands

    def _detect_arch(self):
        """检测系统架构"""
        machine = platform.machine().lower()

        # 处理常见的架构标识
        if machine in ("x86_64", "amd64", "x64"):
            return "x64"
        elif machine in ("aarch64", "arm64"):
            return "aarch64"
        elif machine.startswith("arm"):
            return "arm"
        elif machine in ("i386", "i686", "x86"):
            return "x86"
        else:
            return machine

    def get_arch(self):
        """获取系统架构"""
        return self._arch


# 创建全局实例
platform_manager = PlatformManager()
