import os
import sys
import ctypes
import platform
import subprocess
from abc import ABC, abstractmethod
from loguru import logger
from .platform_manager import platform_manager
from .i18n_manager import i18n_manager
import re
import shutil

# 初始化翻译函数
_ = i18n_manager.get_text

# Windows 特定的导入
if platform.system() == "Windows":
    import winreg
    import win32gui
    import win32con

# 前向声明全局变量
system_manager = None


# 全局函数
def check_admin_rights():
    """检查是否具有管理员权限"""
    return system_manager.check_admin_rights()


def create_symlink(source_path, target_path):
    """创建符号链接
    Args:
        source_path: 源路径
        target_path: 目标路径
    Returns:
        bool: 操作是否成功
    """
    return system_manager.create_symlink(source_path, target_path)


def set_environment_variable(name, value, config_file=None):
    """设置环境变量
    Args:
        name: 环境变量名
        value: 环境变量值
        config_file: 配置文件路径（仅用于Unix系统）
    Returns:
        bool: 操作是否成功
    """
    if isinstance(system_manager, UnixManager):
        return system_manager.set_environment_variable(name, value, config_file)
    return system_manager.set_environment_variable(name, value)


def get_environment_variable(name, config_file=None):
    """获取环境变量值
    Args:
        name: 环境变量名
        config_file: 配置文件路径（仅用于Unix系统）
    Returns:
        str: 环境变量值
    """
    if isinstance(system_manager, UnixManager):
        return system_manager.get_environment_variable(name, config_file)
    return system_manager.get_environment_variable(name)


def update_path_variable(java_home_path, config_file=None):
    """更新 PATH 环境变量
    Args:
        java_home_path: Java home 路径
        config_file: 配置文件路径（仅用于Unix系统）
    Returns:
        bool: 操作是否成功
    """
    if isinstance(system_manager, UnixManager):
        return system_manager.update_path_variable(java_home_path, config_file)
    return system_manager.update_path_variable(java_home_path)


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
    def set_environment_variable(self, name, value, config_file=None):
        """设置系统环境变量"""
        pass

    @abstractmethod
    def get_environment_variable(self, name, config_file=None):
        """获取系统环境变量值"""
        pass

    @abstractmethod
    def update_path_variable(self, new_path, config_file=None):
        """更新PATH环境变量"""
        pass

    def _normalize_path(self, path):
        """规范化路径
        Args:
            path: 需要规范化的路径
        Returns:
            规范化后的路径
        """
        try:
            if not path:
                return None
            # 展开环境变量
            expanded = os.path.expandvars(path)
            # 展开用户目录
            expanded = os.path.expanduser(expanded)
            # 转换为绝对路径
            abs_path = os.path.abspath(expanded)
            # 规范化路径分隔符
            return os.path.normpath(abs_path)
        except Exception as e:
            logger.error(f"路径规范化失败: {str(e)}")
            return path

    def _validate_env_value(self, value):
        """验证环境变量值
        Args:
            value: 环境变量值
        Returns:
            验证后的值
        """
        try:
            if not value:
                return ""
            # 移除不安全字符
            value = re.sub(r"[;&|]", "", value)
            # 规范化路径分隔符
            if platform.system() == "Windows":
                value = value.replace("/", "\\")
            else:
                value = value.replace("\\", "/")
            return value
        except Exception as e:
            logger.error(f"环境变量值验证失败: {str(e)}")
            return value

    def _expand_env_vars(self, value):
        """展开环境变量
        Args:
            value: 包含环境变量的字符串
        Returns:
            展开后的字符串
        """
        try:
            if not value:
                return ""
            # 展开环境变量
            expanded = os.path.expandvars(value)
            # 处理特殊情况
            if platform.system() == "Windows":
                # 处理 Windows 风格的环境变量
                pattern = r"%([^%]+)%"
            else:
                # 处理 Unix 风格的环境变量
                pattern = r"\$\{([^}]+)\}|\$([a-zA-Z_][a-zA-Z0-9_]*)"

            def replace_var(match):
                var_name = match.group(1) or match.group(2)
                return os.environ.get(var_name, match.group(0))

            expanded = re.sub(pattern, replace_var, expanded)
            return expanded
        except Exception as e:
            logger.error(f"环境变量展开失败: {str(e)}")
            return value


class WindowsManager(SystemManager):
    """Windows系统管理器"""

    def _normalize_and_resolve_path(self, path):
        """规范化并解析路径，处理软链接"""
        try:
            if not path:
                return None
            # 规范化路径（处理斜杠、大小写等）
            norm_path = os.path.normpath(os.path.normcase(path))
            if os.path.exists(norm_path):
                # 如果是软链接，获取真实路径
                if os.path.islink(norm_path):
                    real_path = os.path.realpath(norm_path)
                    return os.path.normpath(os.path.normcase(real_path))
                return norm_path
            return None
        except Exception as e:
            logger.error(f"路径规范化失败: {str(e)}")
            return None

    def _are_paths_equal(self, path1, path2):
        """比较两个路径是否指向相同位置"""
        try:
            if not path1 or not path2:
                return False

            # 规范化并解析两个路径
            resolved_path1 = self._normalize_and_resolve_path(path1)
            resolved_path2 = self._normalize_and_resolve_path(path2)

            if not resolved_path1 or not resolved_path2:
                return False

            # 比较规范化后的路径
            return resolved_path1 == resolved_path2
        except Exception as e:
            logger.error(f"路径比较失败: {str(e)}")
            return False

    def check_admin_rights(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def create_symlink(self, source_path, target_path):
        """创建符号链接"""
        try:
            # 检查管理员权限
            if not self.check_admin_rights():
                logger.error("需要管理员权限来创建符号链接")
                return False

            # 规范化路径
            source_path = os.path.normpath(source_path)
            target_path = os.path.normpath(target_path)

            # 检查源路径是否存在
            if not os.path.exists(source_path):
                logger.error(f"源路径不存在: {source_path}")
                return False

            # 检查是否需要更新
            if os.path.exists(target_path):
                # 如果目标已经是正确的软链接，则不需要更新
                if self._are_paths_equal(target_path, source_path):
                    logger.info("软链接已经指向正确的目标，无需更新")
                    return True

                try:
                    import stat

                    os.chmod(target_path, stat.S_IWRITE)
                    if os.path.islink(target_path) or os.path.isdir(target_path):
                        # 如果是目录或符号链接，使用 rmdir
                        if os.path.isdir(target_path) and not os.path.islink(
                            target_path
                        ):
                            os.rmdir(target_path)
                        else:
                            os.unlink(target_path)
                    else:
                        os.remove(target_path)
                except PermissionError as pe:
                    logger.error(f"删除目标路径需要管理员权限: {str(pe)}")
                    return False
                except Exception as e:
                    logger.error(f"删除已存在的目标路径失败: {str(e)}")
                    return False

            # 确保目标路径的父目录存在
            parent_dir = os.path.dirname(target_path)
            if parent_dir and not os.path.exists(parent_dir):
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                    logger.info(f"创建目标父目录: {parent_dir}")
                except PermissionError as pe:
                    logger.error(f"创建目标目录需要管理员权限: {str(pe)}")
                    return False
                except Exception as e:
                    logger.error(f"创建目标目录失败: {str(e)}")
                    return False

            # 使用subprocess执行mklink命令
            try:
                # 使用完整的 cmd.exe 路径
                cmd_path = os.path.join(
                    os.environ.get("SystemRoot", "C:\\Windows"),
                    "System32",
                    "cmd.exe",
                )
                # 不要给路径加引号，让 subprocess 来处理路径转义
                cmd = [cmd_path, "/c", "mklink", "/J", target_path, source_path]
                result = subprocess.run(
                    cmd,
                    shell=False,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else "未知错误"
                    logger.error(f"创建符号链接失败: {error_msg}")
                    # 记录更详细的错误信息
                    logger.debug(f"命令: {' '.join(cmd)}")
                    logger.debug(f"返回码: {result.returncode}")
                    logger.debug(f"标准输出: {result.stdout}")
                    logger.debug(f"标准错误: {result.stderr}")
                    return False
                return True
            except Exception as e:
                logger.error(f"创建Windows符号链接失败: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"创建符号链接失败: {str(e)}")
            return False

    def set_environment_variable(self, name, value, config_file=None):
        try:
            # 检查权限
            if not self.check_admin_rights():
                error_msg = platform_manager.get_error_message("admin_rights")
                logger.error(error_msg)
                return False

            # 规范化路径
            value = os.path.normpath(value)

            # 使用 winreg 更新系统环境变量
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"System\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_ALL_ACCESS,
            ) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)

            # 立即更新当前进程的环境变量
            os.environ[name] = value

            # 发送环境变量更改的广播消息
            # 使用多种方式通知系统环境变量已更改
            try:
                # 方式1: 使用 SendMessageTimeout
                win32gui.SendMessageTimeout(
                    win32con.HWND_BROADCAST,
                    win32con.WM_SETTINGCHANGE,
                    0,
                    "Environment",
                    win32con.SMTO_ABORTIFHUNG,
                    5000,
                )

                # 方式2: 使用 rundll32
                subprocess.run(
                    ["rundll32", "user32.dll,UpdatePerUserSystemParameters"],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

                # 方式3: 使用 explorer
                subprocess.run(
                    ["cmd", "/c", "echo %JAVA_HOME%"],
                    env=dict(os.environ),
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except Exception as e:
                logger.warning(f"发送环境变量更改通知时出现警告（不影响设置）: {str(e)}")

            return True
        except Exception as e:
            logger.error(f"设置环境变量失败: {str(e)}")
            return False

    def get_environment_variable(self, name, config_file=None):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"System\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_READ,
            )
            value, _ = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return value
        except Exception as e:
            logger.error(f"获取环境变量失败: {str(e)}")
            return None

    def update_path_variable(self, new_path, config_file=None):
        try:
            # 检查权限
            if not self.check_admin_rights():
                error_msg = platform_manager.get_error_message("admin_rights")
                logger.error(error_msg)
                return False

            # 规范化路径
            new_path = os.path.normpath(new_path)

            # 获取当前 PATH
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"System\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_READ,
            ) as key:
                current_path, _ = winreg.QueryValueEx(key, "Path")

            # 处理路径列表
            paths = current_path.split(";")
            # 移除空路径和包含 java 或 jdk 的路径
            paths = [
                p
                for p in paths
                if p and not any(x in p.lower() for x in ["java", "jdk"])
            ]

            # 添加新的 Java bin 路径（确保使用 %JAVA_HOME%）
            java_bin_path = r"%JAVA_HOME%\bin"
            if java_bin_path not in paths:
                paths.insert(0, java_bin_path)  # 添加到开头以确保优先级

            # 合并路径，确保没有重复的分号
            new_path_value = ";".join(filter(None, paths))

            # 更新系统环境变量
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"System\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path_value)

            # 立即更新当前进程的环境变量
            expanded_path = os.path.expandvars(new_path_value)  # 展开环境变量
            os.environ["Path"] = expanded_path

            # 发送环境变量更改的广播消息
            try:
                # 方式1: 使用 SendMessageTimeout
                win32gui.SendMessageTimeout(
                    win32con.HWND_BROADCAST,
                    win32con.WM_SETTINGCHANGE,
                    0,
                    "Environment",
                    win32con.SMTO_ABORTIFHUNG,
                    5000,
                )

                # 方式2: 使用 cmd 刷新环境变量
                cmd_path = os.path.join(
                    os.environ.get("SystemRoot", "C:\\Windows"), "System32", "cmd.exe"
                )
                if os.path.exists(cmd_path):
                    try:
                        # 使用 cmd 刷新环境变量
                        subprocess.run(
                            [cmd_path, "/c", "set"],
                            capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            check=True,
                        )
                    except subprocess.CalledProcessError as e:
                        logger.warning(f"CMD 环境变量刷新失败（不影响设置）: {str(e)}")

                # 方式3: 使用 rundll32 刷新系统设置
                subprocess.run(
                    ["rundll32", "user32.dll,UpdatePerUserSystemParameters"],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

            except Exception as e:
                logger.warning(f"发送环境变量更改通知时出现警告（不影响设置）: {str(e)}")

            # 确保环境变量已正确设置
            try:
                # 验证 JAVA_HOME 是否正确设置
                java_home = self.get_environment_variable("JAVA_HOME")
                if java_home:
                    # 更新 PATH 中的 Java bin 路径
                    bin_path = os.path.join(java_home, "bin")
                    if os.path.exists(bin_path):
                        os.environ["PATH"] = (
                            bin_path + os.pathsep + os.environ.get("PATH", "")
                        )
            except Exception as e:
                logger.warning(f"验证环境变量设置时出现警告: {str(e)}")

            return True
        except Exception as e:
            logger.error(f"更新PATH环境变量失败: {str(e)}")
            return False


class UnixManager(SystemManager):
    """Unix系统管理器（Mac/Linux）"""

    def check_admin_rights(self):
        """检查是否有管理员权限"""
        try:
            return os.geteuid() == 0
        except:
            return False

    def create_symlink(self, source_path, target_path):
        """创建符号链接"""
        try:
            # 转换为绝对路径
            source_path = os.path.abspath(source_path)
            target_path = os.path.abspath(target_path)

            # 检查源路径是否存在
            if not os.path.exists(source_path):
                logger.error(f"源路径不存在: {source_path}")
                return False

            if platform.system() == "Darwin":  # macOS
                try:
                    # 确保目标路径的父目录存在
                    target_dir = os.path.dirname(target_path)
                    if not os.path.exists(target_dir):
                        try:
                            os.makedirs(target_dir, exist_ok=True)
                        except PermissionError:
                            # 如果创建目录失败，尝试在用户目录下创建
                            user_home = os.path.expanduser("~")
                            target_dir = os.path.join(user_home, ".jvman", "current")
                            os.makedirs(target_dir, exist_ok=True)
                            target_path = os.path.join(target_dir, os.path.basename(target_path))

                    # 如果目标已存在，先删除
                    if os.path.exists(target_path):
                        try:
                            if os.path.islink(target_path) or os.path.isfile(target_path):
                                os.unlink(target_path)
                            else:
                                shutil.rmtree(target_path)
                        except PermissionError:
                            # 如果删除失败，尝试在用户目录下重新创建
                            user_home = os.path.expanduser("~")
                            target_dir = os.path.join(user_home, ".jvman", "current")
                            os.makedirs(target_dir, exist_ok=True)
                            target_path = os.path.join(target_dir, os.path.basename(target_path))
                            if os.path.exists(target_path):
                                if os.path.islink(target_path) or os.path.isfile(target_path):
                                    os.unlink(target_path)
                                else:
                                    shutil.rmtree(target_path)

                    # 创建软链接
                    try:
                        os.symlink(source_path, target_path)
                        logger.info(f"成功创建软链接: {target_path} -> {source_path}")
                        return True
                    except PermissionError:
                        # 如果在原位置创建失败，尝试在用户目录下创建
                        user_home = os.path.expanduser("~")
                        target_dir = os.path.join(user_home, ".jvman", "current")
                        os.makedirs(target_dir, exist_ok=True)
                        target_path = os.path.join(target_dir, os.path.basename(target_path))
                        os.symlink(source_path, target_path)
                        logger.info(f"成功在用户目录下创建软链接: {target_path} -> {source_path}")
                        return True

                except Exception as e:
                    logger.error(f"创建软链接失败: {str(e)}")
                    # 如果所有尝试都失败了，才使用 sudo
                    try:
                        import base64
                        # 创建命令字符串
                        commands = f"""#!/bin/bash
                        if [ -e "{target_path}" ]; then
                            rm -rf "{target_path}"
                        fi
                        mkdir -p "{os.path.dirname(target_path)}"
                        ln -sfn "{source_path}" "{target_path}"
                        chown -h {os.environ.get('USER', 'root')} "{target_path}"
                        """
                        # 对命令进行 base64 编码
                        encoded_commands = base64.b64encode(commands.encode()).decode()
                        # 使用 osascript 执行解码后的命令
                        cmd = [
                            "osascript",
                            "-e",
                            'do shell script "echo ' + encoded_commands + ' | base64 -D | bash" with administrator privileges',
                        ]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            logger.info("使用管理员权限成功创建软链接")
                            return True
                        else:
                            logger.error(f"使用管理员权限创建软链接失败: {result.stderr}")
                            return False
                    except Exception as e:
                        logger.error(f"使用管理员权限创建软链接失败: {str(e)}")
                        return False

            else:  # Linux
                try:
                    # 首先尝试在用户目录下创建
                    user_home = os.path.expanduser("~")
                    target_dir = os.path.join(user_home, ".jvman", "current")
                    try:
                        os.makedirs(target_dir, exist_ok=True)
                        user_target_path = os.path.join(target_dir, os.path.basename(target_path))
                        
                        # 如果目标已存在，先删除
                        if os.path.exists(user_target_path):
                            if os.path.islink(user_target_path) or os.path.isfile(user_target_path):
                                os.unlink(user_target_path)
                            else:
                                shutil.rmtree(user_target_path)
                        
                        # 创建软链接
                        os.symlink(source_path, user_target_path)
                        logger.info(f"成功在用户目录下创建软链接: {user_target_path} -> {source_path}")
                        return True
                    except Exception as e:
                        logger.warning(f"在用户目录下创建软链接失败，尝试在原目标位置创建: {str(e)}")

                    # 如果在用户目录下创建失败，尝试在原目标位置创建
                    target_dir = os.path.dirname(target_path)
                    if not os.path.exists(target_dir):
                        try:
                            os.makedirs(target_dir, exist_ok=True)
                        except PermissionError:
                            # 使用 sudo 创建目录
                            result = subprocess.run(
                                ["sudo", "mkdir", "-p", target_dir],
                                capture_output=True,
                                text=True,
                            )
                            if result.returncode != 0:
                                logger.error(f"创建目录失败: {result.stderr}")
                                return False

                    # 如果目标已存在，先删除
                    if os.path.exists(target_path):
                        try:
                            if os.path.islink(target_path) or os.path.isfile(target_path):
                                os.unlink(target_path)
                            else:
                                shutil.rmtree(target_path)
                        except PermissionError:
                            # 使用 sudo 删除
                            result = subprocess.run(
                                ["sudo", "rm", "-rf", target_path],
                                capture_output=True,
                                text=True,
                            )
                            if result.returncode != 0:
                                logger.error(f"删除目标路径失败: {result.stderr}")
                                return False

                    # 创建软链接
                    try:
                        os.symlink(source_path, target_path)
                        logger.info(f"成功创建软链接: {target_path} -> {source_path}")
                        return True
                    except PermissionError:
                        # 使用 sudo 创建软链接
                        result = subprocess.run(
                            ["sudo", "ln", "-sfn", source_path, target_path],
                            capture_output=True,
                            text=True,
                        )
                        if result.returncode != 0:
                            logger.error(f"创建软链接失败: {result.stderr}")
                            return False

                        # 修改所有权
                        user = os.environ.get("USER", os.environ.get("USERNAME"))
                        if user:
                            result = subprocess.run(
                                ["sudo", "chown", "-h", user, target_path],
                                capture_output=True,
                                text=True,
                            )
                            if result.returncode != 0:
                                logger.warning(f"修改所有权失败（不影响使用）: {result.stderr}")

                        return True

                except subprocess.CalledProcessError as e:
                    if "sudo: no tty present" in str(e):
                        logger.error("需要交互式终端来执行 sudo 命令")
                    else:
                        logger.error(f"执行命令失败: {str(e)}")
                    return False
                except Exception as e:
                    logger.error(f"创建软链接失败: {str(e)}")
                    return False

        except Exception as e:
            logger.error(f"创建符号链接失败: {str(e)}")
            return False

    def get_environment_variable(self, name, config_file=None):
        """获取系统环境变量值
        Args:
            name: 环境变量名
            config_file: 配置文件路径（仅用于Unix系统）
        """
        try:
            # Unix 系统变量获取逻辑
            home = os.path.expanduser("~")

            # 定义配置文件优先级顺序
            config_files = [
                os.path.join(home, ".bash_profile"),  # 最高优先级
                os.path.join(home, ".bashrc"),
                os.path.join(home, ".profile"),
                "/etc/profile",
                "/etc/bashrc",
                "/etc/environment",
            ]

            # 如果指定了配置文件，则只检查该文件
            if config_file and os.path.exists(config_file):
                config_files = [config_file]

            # 用于存储找到的值和来源
            found_value = None
            found_source = None

            # 遍历所有配置文件
            for config_file in config_files:
                if os.path.exists(config_file):
                    try:
                        with open(config_file, "r") as f:
                            content = f.read()

                        # 使用更精确的正则表达式匹配
                        patterns = [
                            (f"^{name}=([^#\n]+)", "direct"),  # 直接赋值
                            (f"^export\s+{name}=([^#\n]+)", "export"),  # export 赋值
                            (f"^setenv\s+{name}\s+([^#\n]+)", "setenv"),  # csh/tcsh 风格
                            (f'^{name}="([^"]+)"', "quoted"),  # 双引号
                            (f"^{name}='([^']+)'", "quoted"),  # 单引号
                            (
                                f'^export\s+{name}="([^"]+)"',
                                "export_quoted",
                            ),  # export 带双引号
                            (
                                f"^export\s+{name}='([^']+)'",
                                "export_quoted",
                            ),  # export 带单引号
                        ]

                        for pattern, assign_type in patterns:
                            matches = re.finditer(pattern, content, re.MULTILINE)
                            for match in matches:
                                value = match.group(1).strip()

                                # 记录找到的值和来源
                                if found_value is None:
                                    found_value = value
                                    found_source = config_file

                                # 如果在 .bash_profile 中找到，直接使用这个值
                                if config_file.endswith(".bash_profile"):
                                    logger.debug(
                                        f"在 .bash_profile 中找到 {name}={value} (类型: {assign_type})"
                                    )

                                    # 验证和展开环境变量
                                    value = self._validate_env_value(value)
                                    expanded = self._expand_env_vars(value)
                                    if expanded != value:
                                        logger.debug(f"展开环境变量 {value} -> {expanded}")
                                    return expanded

                    except Exception as e:
                        logger.error(f"读取配置文件 {config_file} 失败: {str(e)}")
                        continue

            # 如果找到了值，返回它
            if found_value:
                logger.debug(f"在 {found_source} 中找到 {name}={found_value}")
                # 验证和展开环境变量
                found_value = self._validate_env_value(found_value)
                expanded = self._expand_env_vars(found_value)
                if expanded != found_value:
                    logger.debug(f"展开环境变量 {found_value} -> {expanded}")
                return expanded

            # 最后尝试从当前环境变量获取
            env_value = os.environ.get(name)
            if env_value:
                logger.debug(f"从当前环境变量中获取到 {name}={env_value}")
                return self._validate_env_value(env_value)

            logger.debug(f"未找到环境变量 {name}")
            return _("settings.env.not_set")

        except Exception as e:
            logger.error(f"获取环境变量失败: {str(e)}")
            return _("settings.env.not_set")

    def set_environment_variable(self, name, value, config_file=None):
        """设置系统环境变量"""
        try:
            if self.is_linux:
                # 如果没有指定配置文件，使用默认的配置文件
                if not config_file:
                    # 按优先级尝试配置文件
                    config_files = [
                        os.path.expanduser("~/.bash_profile"),
                        os.path.expanduser("~/.profile"),
                        os.path.expanduser("~/.bashrc"),
                    ]

                    # 选择第一个可写的配置文件
                    for cf in config_files:
                        if os.path.exists(os.path.dirname(cf)) and os.access(
                            os.path.dirname(cf), os.W_OK
                        ):
                            config_file = cf
                            break

                    if not config_file:
                        config_file = os.path.expanduser("~/.bash_profile")

                if not config_file:
                    logger.error("未找到环境变量配置文件")
                    return False

                # 确保配置文件目录存在
                config_dir = os.path.dirname(config_file)
                if not os.path.exists(config_dir):
                    try:
                        os.makedirs(config_dir, exist_ok=True)
                    except Exception as e:
                        logger.error(f"创建配置文件目录失败: {str(e)}")
                        return False

                # 读取现有内容
                content = ""
                if os.path.exists(config_file):
                    with open(config_file, "r") as f:
                        content = f.read()

                # 解析现有的环境变量设置
                lines = content.split("\n")
                new_lines = []
                env_vars = {}

                # 收集所有环境变量设置
                for line in lines:
                    if not line.strip() or line.strip().startswith("#"):
                        continue

                    if "=" in line:
                        parts = line.split("=", 1)
                        var_name = parts[0].strip().replace("export ", "").strip()
                        var_value = parts[1].strip().strip('"').strip("'")
                        env_vars[var_name] = var_value

                # 准备新的环境变量设置
                if name == "JAVA_HOME":
                    env_vars["JAVA_HOME"] = value
                elif name == "PATH":
                    current_path = env_vars.get("PATH", "")
                    if current_path:
                        paths = [
                            p
                            for p in current_path.split(":")
                            if not any(x in p.lower() for x in ["java", "jdk"])
                        ]
                        paths.insert(0, "$JAVA_HOME/bin")
                        env_vars["PATH"] = ":".join(paths)
                    else:
                        env_vars["PATH"] = "$JAVA_HOME/bin:$PATH"
                elif name == "CLASSPATH":
                    env_vars[
                        "CLASSPATH"
                    ] = ".:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar"

                # 重建配置文件内容
                new_content = []
                if not content.startswith("# Created by JVMan"):
                    new_content.append("# Created by JVMan")
                    new_content.append("")

                # 添加环境变量设置
                for var_name, var_value in env_vars.items():
                    if var_value.startswith("$"):
                        new_content.append(f"export {var_name}={var_value}")
                    else:
                        new_content.append(f'export {var_name}="{var_value}"')

                # 写回文件
                try:
                    with open(config_file, "w") as f:
                        f.write("\n".join(new_content) + "\n")
                except PermissionError:
                    # 如果没有写入权限，尝试使用 sudo
                    temp_file = "/tmp/jvman_env_temp"
                    with open(temp_file, "w") as f:
                        f.write("\n".join(new_content) + "\n")

                    result = subprocess.run(
                        ["sudo", "mv", temp_file, config_file],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        logger.error(f"写入配置文件失败: {result.stderr}")
                        return False

                # 立即生效
                try:
                    # 1. 更新当前进程的环境变量
                    os.environ[name] = value
                    if name == "JAVA_HOME":
                        java_bin = os.path.join(value, "bin")
                        current_path = os.environ.get("PATH", "")
                        if java_bin not in current_path.split(":"):
                            os.environ["PATH"] = f"{java_bin}:{current_path}"

                    # 2. 重新加载 shell 配置
                    shell = os.environ.get("SHELL", "/bin/bash")
                    subprocess.run([shell, "-c", f"source {config_file}"], check=True)

                except Exception as e:
                    logger.warning(f"执行环境变量立即生效命令失败（不影响设置）: {str(e)}")

                return True

            # ... existing code for other platforms ...

        except Exception as e:
            logger.error(f"设置环境变量失败: {str(e)}")
            return False

    def update_path_variable(self, new_path, config_file=None):
        """更新PATH环境变量
        Args:
            new_path: 新的PATH值
            config_file: 指定要写入的配置文件路径
        """
        try:
            current_path = os.environ.get("PATH", "")
            paths = current_path.split(os.pathsep)

            # 移除所有包含 java 或 jdk 的路径
            paths = [
                p for p in paths if not any(x in p.lower() for x in ["java", "jdk"])
            ]

            # 添加新的 Java 路径
            java_bin = os.path.join(new_path, "bin")
            if java_bin not in paths:
                paths.insert(0, java_bin)

            # 更新 PATH
            new_path_value = os.pathsep.join(paths)
            return self.set_environment_variable("PATH", new_path_value, config_file)
        except Exception as e:
            logger.error(f"更新 PATH 环境变量失败: {str(e)}")
            return False


# 在文件末尾初始化系统管理器
def create_system_manager():
    """创建系统管理器实例"""
    if platform.system() == "Windows":
        return WindowsManager()
    return UnixManager()


# 初始化全局系统管理器实例
system_manager = create_system_manager()
