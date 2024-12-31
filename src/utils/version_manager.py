import os
import sys
import json
from loguru import logger
from packaging import version

class VersionManager:
    """版本管理器，统一管理应用程序版本信息"""
    
    # 基础版本号（不可修改）
    BASE_VERSION = "1.0.4"
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._load_app_config()
    
    def _get_app_root(self):
        """获取应用程序根目录"""
        if getattr(sys, 'frozen', False):
            # 如果是打包后的环境
            return os.path.dirname(sys.executable)
        else:
            # 如果是开发环境
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    def _load_app_config(self):
        """加载应用程序配置"""
        try:
            # 首先尝试从打包后的config目录加载
            app_root = self._get_app_root()
            config_paths = [
                os.path.join(app_root, 'config', 'app.json'),  # 打包后的路径
                os.path.join(app_root, 'config', 'app.json'),  # 开发环境config目录
            ]
            
            for config_path in config_paths:
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        self._config = json.load(f)
                        # 验证配置文件中的版本号
                        if not self.is_version_compatible(self._config.get('version')):
                            logger.warning(f"Config version {self._config.get('version')} is not compatible with base version {self.BASE_VERSION}")
                            self._config['version'] = self.BASE_VERSION
                        logger.debug(f"Loaded app config from: {config_path}")
                        return
                        
            raise FileNotFoundError("No app.json found in any of the expected locations")
            
        except Exception as e:
            logger.error(f"Failed to load app config: {e}")
            self._config = {
                "version": self.BASE_VERSION,
                "name": "JDK Version Manager",
                "description": "JDK版本管理工具"
            }
    
    def is_version_compatible(self, check_version):
        """检查版本号是否兼容
        
        Args:
            check_version: 要检查的版本号
            
        Returns:
            bool: 如果版本号兼容返回True，否则返回False
        """
        try:
            if not check_version:
                return False
            # 使用 packaging.version 进行版本号比较
            base_ver = version.parse(self.BASE_VERSION)
            check_ver = version.parse(check_version)
            # 主版本号必须相同，次版本号不能小于基础版本
            return (base_ver.major == check_ver.major and 
                   base_ver.minor <= check_ver.minor)
        except Exception:
            return False
    
    @property
    def version(self):
        """获取应用程序版本号"""
        return self._config.get('version', self.BASE_VERSION)
    
    @property
    def base_version(self):
        """获取基础版本号（不可修改）"""
        return self.BASE_VERSION
    
    @property
    def app_name(self):
        """获取应用程序名称"""
        return self._config.get('name', 'JDK Version Manager')
    
    @property
    def description(self):
        """获取应用程序描述"""
        return self._config.get('description', 'JDK版本管理工具')
    
    @property
    def app_id(self):
        """获取应用程序ID"""
        return self._config.get('build', {}).get('app_id', 'com.jvman.app')
    
    @property
    def copyright(self):
        """获取版权信息"""
        return self._config.get('build', {}).get('copyright', 'Copyright © 2024')
    
    @property
    def changelog(self):
        """获取更新日志"""
        return self._config.get('changelog', [])
    
    def get_latest_changes(self):
        """获取最新版本的更新内容"""
        if self.changelog:
            return self.changelog[0]
        return None
    
    def check_update_available(self):
        """检查是否有更新可用"""
        try:
            config_version = version.parse(self.version)
            base_version = version.parse(self.BASE_VERSION)
            return config_version > base_version
        except Exception:
            return False

# 创建全局实例
version_manager = VersionManager() 