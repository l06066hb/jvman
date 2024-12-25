import os
import json
from loguru import logger

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')
        self.config_file = os.path.join(self.config_dir, 'settings.json')
        self.default_config = {
            'jdk_store_path': os.path.join(os.path.expanduser('~'), 'jdk_versions'),
            'junction_path': os.path.join(os.path.expanduser('~'), 'current_jdk'),
            'theme': 'light',
            'mapped_jdks': [],
            'downloaded_jdks': []
        }
        self.config = self.load_config()

    def load_config(self):
        """加载配置"""
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)
            
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置，确保所有必要的键都存在
                    return {**self.default_config, **config}
            return self.default_config.copy()
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            return self.default_config.copy()

    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            return False

    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)

    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value
        return self.save_config()

    def add_mapped_jdk(self, jdk_info):
        """添加映射的JDK"""
        mapped_jdks = self.get('mapped_jdks', [])
        if jdk_info not in mapped_jdks:
            mapped_jdks.append(jdk_info)
            self.set('mapped_jdks', mapped_jdks)
            return True
        return False

    def add_downloaded_jdk(self, jdk_info):
        """添加下载的JDK"""
        downloaded_jdks = self.get('downloaded_jdks', [])
        if jdk_info not in downloaded_jdks:
            downloaded_jdks.append(jdk_info)
            self.set('downloaded_jdks', downloaded_jdks)
            return True
        return False

    def remove_jdk(self, jdk_path, is_mapped=True):
        """移除JDK记录"""
        key = 'mapped_jdks' if is_mapped else 'downloaded_jdks'
        jdks = self.get(key, [])
        jdks = [jdk for jdk in jdks if jdk['path'] != jdk_path]
        return self.set(key, jdks)

    def get_all_jdks(self):
        """获取所有JDK列表"""
        mapped_jdks = self.get('mapped_jdks', [])
        downloaded_jdks = self.get('downloaded_jdks', [])
        return mapped_jdks + downloaded_jdks 

    def get_current_jdk(self):
        """获取当前使用的JDK信息"""
        junction_path = self.get('junction_path')
        if not junction_path or not os.path.exists(junction_path):
            return None
            
        try:
            # 获取软链接指向的实际路径
            real_path = os.path.realpath(junction_path)
            
            # 在所有JDK中查找匹配的
            for jdk in self.get_all_jdks():
                try:
                    if os.path.samefile(jdk['path'], real_path):
                        return jdk
                except Exception:
                    continue
                    
            return None
        except Exception as e:
            logger.error(f"获取当前JDK失败: {str(e)}")
            return None 