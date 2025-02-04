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
                    # 确保目标路径没有只读属性
                    if platform_manager.is_windows:
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

            if platform_manager.is_windows:
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
            else:
                # Unix系统使用os.symlink
                try:
                    os.symlink(source_path, target_path, target_is_directory=True)
                    return True
                except Exception as e:
                    logger.error(f"创建Unix符号链接失败: {str(e)}")
                    return False
        except Exception as e:
            logger.error(f"创建符号链接失败: {str(e)}")
            return False

    def set_environment_variable(self, name, value):
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

    def get_environment_variable(self, name):
        try:
            import winreg

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

    def update_path_variable(self, new_path):
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
            error_msg = platform_manager.get_error_message(
                "symlink_failed", detail=str(e)
            )
            logger.error(error_msg)
            return False

    def set_environment_variable(self, name, value):
        try:
            config_file = platform_manager.get_shell_config_file()
            if not config_file:
                raise Exception("无法确定shell配置文件位置")

            # 读取现有内容
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    lines = f.readlines()
            else:
                lines = []

            # 根据不同shell生成导出命令
            if platform_manager.shell == "fish":
                export_cmd = f'set -x {name} "{value}"\n'
                path_cmd = f'set -x PATH $PATH "{os.path.join("$" + name, "bin")}"\n'
                lines = [
                    line
                    for line in lines
                    if not line.startswith(f"set -x {name} ")
                    and not (name == "JAVA_HOME" and "set -x PATH" in line)
                ]
            else:
                export_cmd = f'export {name}="{value}"\n'
                if name == "JAVA_HOME":
                    path_cmd = f'export PATH="$PATH:${name}/bin"\n'
                else:
                    path_cmd = None
                lines = [
                    line
                    for line in lines
                    if not line.startswith(f"export {name}=")
                    and not (
                        name == "JAVA_HOME"
                        and "export PATH" in line
                        and "JAVA_HOME" in line
                    )
                ]

            # 添加新的设置
            lines.append(export_cmd)
            if path_cmd:
                lines.append(path_cmd)

            # 写入文件
            with open(config_file, "w") as f:
                f.writelines(lines)

            # 立即生效
            os.environ[name] = value
            if name == "JAVA_HOME":
                current_path = os.environ.get("PATH", "")
                bin_path = os.path.join(value, "bin")
                if bin_path not in current_path:
                    os.environ["PATH"] = f"{current_path}:{bin_path}"

            return True
        except Exception as e:
            error_msg = platform_manager.get_error_message(
                "env_var_failed", detail=str(e)
            )
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
            current_path = self.get_environment_variable("PATH")
            if current_path:
                paths = current_path.split(":")
                # 移除所有包含 java 或 jdk 的路径
                paths = [
                    p for p in paths if not any(x in p.lower() for x in ["java", "jdk"])
                ]
                # 添加新路径到开头
                if new_path not in paths:
                    paths.insert(0, new_path)
                new_path_value = ":".join(filter(None, paths))

                # 根据不同shell生成配置
                config_file = platform_manager.get_shell_config_file()
                if not config_file:
                    raise Exception("无法确定shell配置文件位置")

                # 读取现有内容
                if os.path.exists(config_file):
                    with open(config_file, "r") as f:
                        lines = f.readlines()
                else:
                    lines = []

                # 根据不同shell生成PATH设置命令
                if platform_manager.shell == "fish":
                    path_cmd = f"set -x PATH {new_path_value}\n"
                    lines = [
                        line for line in lines if not line.startswith("set -x PATH ")
                    ]
                else:
                    path_cmd = f'export PATH="{new_path_value}"\n'
                    lines = [
                        line for line in lines if not line.startswith("export PATH=")
                    ]

                # 添加新的PATH设置
                lines.append(path_cmd)

                # 写入文件
                with open(config_file, "w") as f:
                    f.writelines(lines)

                # 立即生效
                os.environ["PATH"] = new_path_value

                return True
            return False
        except Exception as e:
            error_msg = platform_manager.get_error_message(
                "env_var_failed", detail=str(e)
            )
            logger.error(error_msg)
            return False


def get_system_manager():
    """获取对应平台的系统管理器"""
    system = platform.system()
    if system == "Windows":
        return WindowsManager()
    elif system in ["Linux", "Darwin"]:
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
        current_path = os.environ.get("PATH", "")
        paths = current_path.split(os.pathsep)

        # 移除所有包含 java 或 jdk 的路径
        paths = [p for p in paths if not any(x in p.lower() for x in ["java", "jdk"])]

        # 添加新的 Java 路径（使用 %JAVA_HOME%\bin）
        paths.insert(0, "%JAVA_HOME%\\bin")

        # 合并并更新 PATH
        new_path = os.pathsep.join(paths)

        # 使用 winreg 更新系统环境变量
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment",
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_READ,
        ) as key:
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)

        # 发送环境变量更改的广播消息
        win32gui.SendMessageTimeout(
            win32con.HWND_BROADCAST,
            win32con.WM_SETTINGCHANGE,
            0,
            "Environment",
            win32con.SMTO_ABORTIFHUNG,
            5000,
        )

        return True
    except Exception as e:
        logger.error(f"更新 PATH 环境变量失败: {str(e)}")
        return False
