import os
import json
from loguru import logger
import sys
import re
import winreg


class ConfigManager:
    """配置管理器（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.user_config = {}  # 用户配置
            self.app_config = {}  # 程序配置
            self.user_config_file = self._get_user_config_file()
            self.app_config_file = self._get_app_config_file()
            self.load()
            self.initialized = True

    def _get_user_config_file(self):
        """获取用户配置文件路径"""
        user_home = os.path.expanduser("~")
        if sys.platform == "win32":
            config_dir = os.path.join(os.getenv("APPDATA", user_home), "jvman")
        else:
            config_dir = os.path.join(user_home, ".config", "jvman")

        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "settings.json")

    def _get_app_config_file(self):
        """获取程序配置文件路径"""
        if getattr(sys, "frozen", False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        return os.path.join(base_path, "config", "app.json")

    def load(self):
        """加载配置"""
        self._load_app_config()
        self._load_user_config()

    def _load_app_config(self):
        """加载程序配置"""
        try:
            # 获取可能的配置文件路径
            app_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            config_paths = [
                os.path.join(app_dir, "config", "app.json"),  # 开发环境
                os.path.join(app_dir, "bin", "config", "app.json"),  # 打包后的环境
            ]

            # 尝试加载配置文件
            for config_path in config_paths:
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        self.app_config = json.load(f)
                        logger.debug(f"加载程序配置文件: {config_path}")
                        return True

            logger.error(f"程序配置文件不存在: {config_paths[-1]}")
            return False

        except Exception as e:
            logger.error(f"加载程序配置文件失败: {str(e)}")
            return False

    def _load_user_config(self):
        """加载用户配置"""
        try:
            if os.path.exists(self.user_config_file):
                with open(self.user_config_file, "r", encoding="utf-8") as f:
                    self.user_config = json.load(f)
                logger.debug(f"用户配置加载成功: {self.user_config_file}")
            else:
                logger.warning(f"用户配置文件不存在: {self.user_config_file}")
                self._create_default_user_config()
        except Exception as e:
            logger.error(f"加载用户配置失败: {str(e)}")
            self._create_default_user_config()

    def save(self):
        """保存用户配置"""
        try:
            os.makedirs(os.path.dirname(self.user_config_file), exist_ok=True)
            with open(self.user_config_file, "w", encoding="utf-8") as f:
                json.dump(self.user_config, f, indent=4, ensure_ascii=False)
            logger.debug(f"用户配置保存成功: {self.user_config_file}")
        except Exception as e:
            logger.error(f"保存用户配置失败: {str(e)}")

    def get(self, key, default=None):
        """获取配置项
        优先从用户配置获取，如果不存在则从程序配置获取
        """
        try:
            keys = key.split(".")

            # 优先从用户配置获取
            value = self.user_config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        break
                else:
                    value = None
                    break

            # 如果用户配置中没有，从程序配置获取
            if value is None:
                value = self.app_config
                for k in keys:
                    if isinstance(value, dict):
                        value = value.get(k)
                        if value is None:
                            if k == "theme":  # 主题配置特殊处理
                                return "cyan"
                            return default
                    else:
                        if k == "theme":  # 主题配置特殊处理
                            return "cyan"
                        return default

            return value if value is not None else default

        except Exception:
            if key == "theme":  # 主题配置特殊处理
                return "cyan"
            return default

    def set(self, key, value):
        """设置用户配置项"""
        try:
            keys = key.split(".")
            config = self.user_config
            for k in keys[:-1]:
                config = config.setdefault(k, {})
            config[keys[-1]] = value
            return True
        except Exception as e:
            logger.error(f"设置配置失败: {str(e)}")
            return False

    def _create_default_user_config(self):
        """创建默认用户配置"""
        from .version_manager import version_manager

        self.user_config = {
            "language": version_manager.get_default_language(),
            "theme": "cyan",
            "jdk_store_path": "jdk",
            "junction_path": "current",
            "mapped_jdks": [],
            "downloaded_jdks": [],
            "jdks": [],
            "auto_start": False,
            "close_action": None,
            "auto_set_java_home": True,
            "auto_set_path": True,
            "auto_set_classpath": True,
            "update": {"auto_check": True, "last_check_time": None},
        }
        self.save()

    def add_mapped_jdk(self, jdk_info):
        """添加映射的JDK"""
        mapped_jdks = self.get("mapped_jdks", [])

        # 确保路径是绝对路径
        if "path" in jdk_info:
            jdk_info["path"] = os.path.abspath(jdk_info["path"])

        # 确保版本信息完整
        if "version" in jdk_info and not jdk_info["version"].startswith("1."):
            # 对于JDK 9及以上版本，保持原样
            version = jdk_info["version"]
        else:
            # 对于JDK 8及以下版本，确保使用完整版本号
            path = jdk_info.get("path", "")
            if "jdk1.8" in path:
                version_match = re.search(r"jdk1\.8\.0_(\d+)", path)
                if version_match:
                    version = f"1.8.0_{version_match.group(1)}"
                else:
                    version = "1.8.0"
            else:
                version = jdk_info.get("version", "")

        jdk_info["version"] = version

        # 检查是否已存在相同路径的JDK（使用绝对路径比较）
        for existing_jdk in mapped_jdks:
            try:
                existing_path = os.path.abspath(existing_jdk["path"])
                if os.path.samefile(existing_path, jdk_info["path"]):
                    # 更新现有JDK的信息
                    existing_jdk.update(jdk_info)
                    self.set("mapped_jdks", mapped_jdks)
                    return True
            except Exception:
                continue

        mapped_jdks.append(jdk_info)
        self.set("mapped_jdks", mapped_jdks)
        return True

    def add_downloaded_jdk(self, jdk_info):
        """添加下载的JDK"""
        try:
            self.load()  # 重新加载配置
            downloaded_jdks = self.get("downloaded_jdks", [])

            # 确保路径是绝对路径
            if "path" in jdk_info:
                jdk_info["path"] = os.path.abspath(jdk_info["path"])

            # 确保版本信息完整
            if "version" in jdk_info and not jdk_info["version"].startswith("1."):
                version = jdk_info["version"]
            else:
                path = jdk_info.get("path", "")
                if "jdk1.8" in path:
                    version_match = re.search(r"jdk1\.8\.0_(\d+)", path)
                    if version_match:
                        version = f"1.8.0_{version_match.group(1)}"
                    else:
                        version = "1.8.0"
                else:
                    version = jdk_info.get("version", "")

            jdk_info["version"] = version

            # 检查是否已存在相同路径的JDK（使用绝对路径比较）
            for existing_jdk in downloaded_jdks:
                try:
                    existing_path = os.path.abspath(existing_jdk["path"])
                    if os.path.samefile(existing_path, jdk_info["path"]):
                        # 更新现有JDK的信息
                        existing_jdk.update(jdk_info)
                        self.set("downloaded_jdks", downloaded_jdks)
                        logger.debug(f"更新已存在的JDK信息: {jdk_info}")
                        return True
                except Exception:
                    continue

            # 检查是否已存在相同版本和发行商的JDK
            vendor = jdk_info.get("vendor", "")
            arch = jdk_info.get("arch", "")
            for existing_jdk in downloaded_jdks:
                if (
                    existing_jdk.get("vendor") == vendor
                    and existing_jdk.get("version") == version
                    and existing_jdk.get("arch") == arch
                ):
                    # 如果存在，返回错误信息
                    display_name = existing_jdk.get(
                        "display_name", f"{vendor} JDK {version}"
                    )
                    return False, _("download.error.already_exists").format(
                        vendor=vendor,
                        version=version,
                        path=os.path.abspath(existing_jdk["path"]),
                    )

            # 如果没有 display_name，生成一个
            if "display_name" not in jdk_info:
                full_version = jdk_info.get("full_version", version)
                arch = jdk_info.get("arch", "")
                jdk_info["display_name"] = f"{vendor} JDK {full_version} ({arch})"

            jdk_info["type"] = "downloaded"
            downloaded_jdks.append(jdk_info)
            self.set("downloaded_jdks", downloaded_jdks)
            logger.debug(f"成功添加下载的JDK: {jdk_info}")
            return True

        except Exception as e:
            logger.error(f"添加下载的JDK失败: {str(e)}")
            raise Exception(f"添加下载的JDK失败: {str(e)}")

    def remove_jdk(self, jdk_path, is_mapped=False):
        """从配置中移除JDK"""
        try:
            if is_mapped:
                mapped_jdks = self.get("mapped_jdks", [])
                self.set(
                    "mapped_jdks",
                    [jdk for jdk in mapped_jdks if jdk["path"] != jdk_path],
                )
            else:
                downloaded_jdks = self.get("downloaded_jdks", [])
                self.set(
                    "downloaded_jdks",
                    [jdk for jdk in downloaded_jdks if jdk["path"] != jdk_path],
                )
                jdks = self.get("jdks", [])
                self.set("jdks", [jdk for jdk in jdks if jdk["path"] != jdk_path])

            self.save()
            return True
        except Exception as e:
            logger.error(f"从配置中移除JDK失败: {str(e)}")
            raise Exception(f"从配置中移除JDK失败: {str(e)}")

    def get_all_jdks(self):
        """获取所有JDK列表"""
        try:
            self.load()  # 重新加载配置

            jdks = []

            # 获取映射的JDK
            mapped_jdks = self.get("mapped_jdks", [])
            for jdk in mapped_jdks:
                if not jdk.get("type"):
                    jdk["type"] = "mapped"
                jdks.append(jdk)

            # 获取下载的JDK
            downloaded_jdks = self.get("downloaded_jdks", [])
            for jdk in downloaded_jdks:
                if not jdk.get("type"):
                    jdk["type"] = "downloaded"
                jdks.append(jdk)

            # 获取其他JDK
            other_jdks = self.get("jdks", [])
            jdks.extend(other_jdks)

            # 过滤重复的JDK
            unique_jdks = []
            paths = set()
            for jdk in jdks:
                if jdk["path"] not in paths:
                    paths.add(jdk["path"])
                    unique_jdks.append(jdk)

            return unique_jdks
        except Exception as e:
            logger.error(f"获取JDK列表失败: {str(e)}")
            return []

    def get_current_jdk(self):
        """获取当前使用的JDK信息"""
        junction_path = self.get("junction_path")
        if not junction_path or not os.path.exists(junction_path):
            return None

        try:
            # 获取软链接指向的实际路径
            real_path = os.path.realpath(junction_path)

            # 在所有JDK中查找匹配的
            for jdk in self.get_all_jdks():
                try:
                    if os.path.samefile(jdk["path"], real_path):
                        return jdk
                except Exception:
                    continue

            return None
        except Exception as e:
            logger.error(f"获取当前JDK失败: {str(e)}")
            return None

    def set_auto_start(self, enabled):
        """设置自启动状态"""
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "JDK Version Manager"
            exe_path = os.path.abspath(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "jvman.exe",
                )
            )

            # 打开注册表项
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
            )

            if enabled:
                # 添加自启动项
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    # 删除自启动项
                    winreg.DeleteValue(key, app_name)
                except WindowsError:
                    pass  # 如果键不存在，忽略错误

            winreg.CloseKey(key)
            self.set("auto_start", enabled)
            return True
        except Exception as e:
            logger.error(f"设置自启动失败: {str(e)}")
            return False

    def get_auto_start_status(self):
        """获取自启动状态"""
        if sys.platform == "win32":
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_READ,
                )
                try:
                    value, _ = winreg.QueryValueEx(key, "JVMan")
                    return True
                except WindowsError:
                    return False
                finally:
                    winreg.CloseKey(key)
            except WindowsError:
                return False
        else:
            # 在 Linux/macOS 上检查自启动配置
            user_home = os.path.expanduser("~")
            autostart_dir = os.path.join(user_home, ".config", "autostart")
            desktop_file = os.path.join(autostart_dir, "jvman.desktop")
            return os.path.exists(desktop_file)

    def get_config_dir(self):
        """获取配置目录路径"""
        user_home = os.path.expanduser("~")
        if sys.platform == "win32":
            config_dir = os.path.join(os.getenv("APPDATA", user_home), "jvman")
        else:
            config_dir = os.path.join(user_home, ".config", "jvman")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def add_jdk(self, jdk_info):
        """添加JDK到配置"""
        try:
            # 确保版本信息完整
            if "version" in jdk_info and not jdk_info["version"].startswith("1."):
                # 对于JDK 9及以上版本，保持原样
                version = jdk_info["version"]
            else:
                # 对于JDK 8及以下版本，确保使用完整版本号
                path = jdk_info.get("path", "")
                if "jdk1.8" in path:
                    version_match = re.search(r"jdk1\.8\.0_(\d+)", path)
                    if version_match:
                        version = f"1.8.0_{version_match.group(1)}"
                    else:
                        version = "1.8.0"
                else:
                    version = jdk_info.get("version", "")

            jdk_info["version"] = version

            if jdk_info.get("type") == "mapped":
                return self.add_mapped_jdk(jdk_info)
            elif jdk_info.get("type") == "downloaded":
                return self.add_downloaded_jdk(jdk_info)
            else:
                # 获取当前的JDK列表
                jdks = self.get("jdks", [])

                # 检查是否已存在相同路径的JDK
                for jdk in jdks:
                    if jdk["path"] == jdk_info["path"]:
                        # 如果存在，更新信息
                        jdk.update(jdk_info)
                        self.save()
                        return True

                # 如果不存在，添加到列表
                jdks.append(jdk_info)
                self.set("jdks", jdks)
                return True

        except Exception as e:
            logger.error(f"添加JDK到配置失败: {str(e)}")
            raise Exception(f"添加JDK到配置失败: {str(e)}")
