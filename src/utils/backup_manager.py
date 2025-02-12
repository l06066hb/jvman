import os
import json
import time
import platform
import shutil
from loguru import logger
from .platform_manager import platform_manager
from .config_manager import ConfigManager
from .i18n_manager import i18n_manager

# 初始化翻译函数
_ = i18n_manager.get_text

# Windows 特定的导入
if platform.system() == "Windows":
    import winreg
    import win32gui
    import win32con


class BackupManager:
    """环境变量备份管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.config_manager = ConfigManager()
            self.backup_dir = os.path.join(
                self.config_manager.get_config_dir(), "backups", "env"
            )
            # 最大备份数量限制
            self.max_backups = 5  # 保留最近5个备份
            os.makedirs(self.backup_dir, exist_ok=True)
            self.initialized = True

    def create_backup(self, backup_type="auto"):
        """创建环境变量备份
        Args:
            backup_type: 备份类型，"auto"为自动备份，"manual"为手动备份
        Returns:
            bool: 是否成功
        """
        try:
            # 检查备份数量
            backups = self.get_backup_list()
            if len(backups) >= self.max_backups and backup_type == "auto":
                logger.warning(f"自动备份数量已达到上限({self.max_backups}个)，将删除最旧的备份")

            # 生成备份文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"env_backup_{backup_type}_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)

            # 获取当前环境变量值
            java_home = os.environ.get("JAVA_HOME", "")
            classpath = os.environ.get("CLASSPATH", "")
            path = os.environ.get("PATH", "")

            # 创建备份信息
            backup_info = {
                "timestamp": timestamp,
                "type": backup_type,
                "platform": platform.system(),
                "env_vars": {},
                "current_values": {
                    "JAVA_HOME": java_home,
                    "CLASSPATH": classpath,
                    "PATH": path,
                },
            }

            if platform_manager.is_windows:
                # Windows: 备份注册表环境变量
                backup_info["env_vars"] = self._backup_windows_env()
                backup_info["config_type"] = "Windows Registry"
            else:
                # Unix: 备份当前使用的配置文件
                config_file = platform_manager.get_shell_config_file()
                if config_file:
                    backup_info["env_vars"] = self._backup_unix_env(config_file)
                    backup_info["config_type"] = os.path.basename(config_file)
                else:
                    backup_info["config_type"] = "Unknown"

            # 保存备份文件
            with open(f"{backup_path}.json", "w", encoding="utf-8") as f:
                json.dump(backup_info, f, indent=4, ensure_ascii=False)

            # 清理旧备份
            self._cleanup_old_backups()

            logger.info(f"创建备份成功: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}")
            return False

    def restore_backup(self, backup_name):
        """恢复环境变量备份
        Args:
            backup_name: 备份文件名
        Returns:
            bool: 是否成功
        """
        try:
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.json")

            # 读取备份文件
            with open(backup_path, "r", encoding="utf-8") as f:
                backup_info = json.load(f)

            # 检查平台是否匹配
            if backup_info["platform"] != platform.system():
                raise Exception(_("backup.error.platform_mismatch"))

            # 恢复环境变量
            if platform_manager.is_windows:
                self._restore_windows_env(backup_info["env_vars"])
            else:
                self._restore_unix_env(backup_info["env_vars"])

            logger.info(f"恢复备份成功: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"恢复备份失败: {str(e)}")
            return False

    def get_backup_list(self):
        """获取备份列表
        Returns:
            list: 备份列表，按时间倒序排序
        """
        try:
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.endswith(".json"):
                    backup_path = os.path.join(self.backup_dir, file)
                    with open(backup_path, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        # 获取配置文件路径
                        config_files = []
                        if platform_manager.is_windows:
                            config_files.append("Windows Registry")
                        else:
                            for config_file, file_info in info.get(
                                "env_vars", {}
                            ).items():
                                config_files.append(
                                    file_info.get(
                                        "display_name", os.path.basename(config_file)
                                    )
                                )

                        backups.append(
                            {
                                "name": file[:-5],  # 移除.json后缀
                                "timestamp": info["timestamp"],
                                "type": info["type"],
                                "platform": info["platform"],
                                "config_files": config_files,  # 添加配置文件列表
                                "current_values": info.get("current_values", {}),
                            }
                        )

            # 按时间戳排序
            backups.sort(key=lambda x: x["timestamp"], reverse=True)
            return backups

        except Exception as e:
            logger.error(f"获取备份列表失败: {str(e)}")
            return []

    def _backup_windows_env(self):
        """备份Windows环境变量
        Returns:
            dict: 环境变量信息
        """
        env_vars = {}
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"System\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_READ,
            ) as key:
                # 获取所有环境变量
                i = 0
                while True:
                    try:
                        name, value, type = winreg.EnumValue(key, i)
                        env_vars[name] = {"value": value, "type": type}
                        i += 1
                    except WindowsError:
                        break

            return env_vars

        except Exception as e:
            logger.error(f"备份Windows环境变量失败: {str(e)}")
            return {}

    def _backup_unix_env(self, config_file):
        """备份Unix环境变量配置文件
        Args:
            config_file: 当前使用的配置文件路径
        Returns:
            dict: 环境变量信息
        """
        env_vars = {}
        try:
            if os.path.exists(config_file):
                # 只备份当前使用的配置文件
                with open(config_file, "r") as f:
                    env_vars[config_file] = {
                        "type": "file",
                        "content": f.read(),
                        "permissions": oct(os.stat(config_file).st_mode)[-3:],
                        "display_name": os.path.basename(config_file),  # 添加显示名称
                    }
                logger.debug(f"已备份配置文件: {config_file}")
                return env_vars

        except Exception as e:
            logger.error(f"备份Unix环境变量失败: {str(e)}")
            return {}

    def _restore_windows_env(self, env_vars):
        """恢复Windows环境变量
        Args:
            env_vars: 环境变量信息
        """
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"System\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                for name, info in env_vars.items():
                    winreg.SetValueEx(key, name, 0, info["type"], info["value"])

            # 发送环境变量更改通知
            win32gui.SendMessageTimeout(
                win32con.HWND_BROADCAST,
                win32con.WM_SETTINGCHANGE,
                0,
                "Environment",
                win32con.SMTO_ABORTIFHUNG,
                5000,
            )

        except Exception as e:
            raise Exception(f"恢复Windows环境变量失败: {str(e)}")

    def _restore_unix_env(self, env_vars):
        """恢复Unix环境变量配置文件
        Args:
            env_vars: 环境变量信息
        """
        try:
            # 恢复每个配置文件
            for config_file, info in env_vars.items():
                try:
                    # 创建备份
                    if os.path.exists(config_file):
                        backup_suffix = time.strftime("%Y%m%d_%H%M%S")
                        backup_path = f"{config_file}.before_restore.{backup_suffix}"
                        if os.path.isdir(config_file):
                            shutil.copytree(config_file, backup_path)
                        else:
                            shutil.copy2(config_file, backup_path)

                    # 恢复文件或目录
                    if info["type"] == "directory":
                        os.makedirs(config_file, exist_ok=True)
                        for file_name, content in info["content"].items():
                            file_path = os.path.join(config_file, file_name)
                            with open(file_path, "w") as f:
                                f.write(content)
                    else:
                        # 确保父目录存在
                        os.makedirs(os.path.dirname(config_file), exist_ok=True)
                        with open(config_file, "w") as f:
                            f.write(info["content"])
                        # 恢复权限
                        if "permissions" in info:
                            os.chmod(config_file, int(info["permissions"], 8))

                    logger.info(f"已恢复配置文件: {config_file}")
                except Exception as e:
                    logger.error(f"恢复配置文件 {config_file} 失败: {str(e)}")
                    continue

            # 重新加载环境变量
            shell = os.environ.get("SHELL", "")
            if shell:
                try:
                    os.system(
                        f"{shell} -c 'source ~/.bashrc 2>/dev/null || source ~/.bash_profile 2>/dev/null || source ~/.profile 2>/dev/null'"
                    )
                except Exception as e:
                    logger.warning(f"重新加载环境变量失败: {str(e)}")

        except Exception as e:
            raise Exception(f"恢复Unix环境变量失败: {str(e)}")

    def _cleanup_old_backups(self):
        """清理旧备份"""
        try:
            backups = self.get_backup_list()
            if len(backups) > self.max_backups:
                # 删除多余的备份
                for backup in backups[self.max_backups :]:
                    backup_path = os.path.join(
                        self.backup_dir, f"{backup['name']}.json"
                    )
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                        logger.info(f"删除旧备份: {backup_path}")

        except Exception as e:
            logger.error(f"清理旧备份失败: {str(e)}")

    def get_backup_content(self, backup_name):
        """获取备份内容
        Args:
            backup_name: 备份名称
        Returns:
            dict: 备份内容
        """
        try:
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.json")
            if not os.path.exists(backup_path):
                return None

            with open(backup_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"获取备份内容失败: {str(e)}")
            return None

    def get_current_env_values(self):
        """获取当前环境变量值
        Returns:
            dict: 当前环境变量值
        """
        return {
            "JAVA_HOME": os.environ.get("JAVA_HOME", ""),
            "CLASSPATH": os.environ.get("CLASSPATH", ""),
            "PATH": os.environ.get("PATH", ""),
        }
