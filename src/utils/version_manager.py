import os
import sys
import json
from loguru import logger
from packaging import version


class VersionManager:
    """版本管理器"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not VersionManager._initialized:
            VersionManager._initialized = True
            self.version = "0.0.0"  # 默认版本号，实际从配置文件加载
            self.default_language = "zh_CN"  # 默认语言
            self.supported_languages = ["zh_CN", "en_US"]  # 支持的语言列表
            self._app_info = {
                "name": "JDK Version Manager",
                "description": "JDK版本管理工具",
                "copyright": "Copyright © 2024",
                "build": {"app_id": "com.jvman.app"},
            }
            self._load_version_info()

    def _load_version_info(self):
        """加载版本信息"""
        try:
            # 获取配置文件路径
            if getattr(sys, "frozen", False):
                # 如果是打包后的环境
                base_path = os.path.dirname(os.path.dirname(sys._MEIPASS))
            else:
                # 如果是开发环境
                base_path = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )

            # 尝试多个可能的配置文件位置
            config_paths = [
                os.path.join(base_path, "config", "app.json"),  # 标准位置
                os.path.join(base_path, "app.json"),  # 根目录
                os.path.join(sys._MEIPASS, "config", "app.json")
                if getattr(sys, "frozen", False)
                else None,  # 打包后的位置
            ]

            config_file = None
            for path in config_paths:
                if path and os.path.exists(path):
                    config_file = path
                    break

            if config_file:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.version = config.get("version", self.version)
                    # 从配置文件获取语言相关设置
                    if "features" in config and "i18n" in config["features"]:
                        self.supported_languages = config["features"]["i18n"]
                        if self.supported_languages:
                            self.default_language = self.supported_languages[0]
                    # 加载应用信息
                    if "name" in config:
                        self._app_info["name"] = config["name"]
                    if "description" in config:
                        self._app_info["description"] = config["description"]
                    if "copyright" in config:
                        self._app_info["copyright"] = config["copyright"]
                    if "build" in config:
                        self._app_info["build"].update(config["build"])
            else:
                logger.warning("No app.json configuration file found")
        except Exception as e:
            logger.error(f"Failed to load version info: {str(e)}")

    def get_version(self):
        """获取当前版本号"""
        return self.version

    def get_default_language(self):
        """获取默认语言"""
        return self.default_language

    def get_supported_languages(self):
        """获取支持的语言列表"""
        return self.supported_languages

    def check_version(self, version_str):
        """检查版本号是否大于当前版本"""
        try:
            current = version.parse(self.version)
            new = version.parse(version_str)
            return new > current
        except Exception as e:
            logger.error(f"Version check failed: {str(e)}")
            return False

    @property
    def app_name(self):
        """获取应用程序名称"""
        return self._app_info["name"]

    @property
    def description(self):
        """获取应用程序描述"""
        return self._app_info["description"]

    @property
    def copyright(self):
        """获取版权信息"""
        return self._app_info["copyright"]

    @property
    def app_id(self):
        """获取应用程序ID"""
        return self._app_info["build"]["app_id"]


# 创建全局实例
version_manager = VersionManager()
