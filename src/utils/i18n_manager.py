import os
import json
from loguru import logger

class I18nManager:
    """国际化管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.i18n_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'i18n')
            self.current_lang = 'zh_CN'
            self.translations = {}
            self.load_translations()
    
    def load_translations(self):
        """加载所有语言文件"""
        try:
            for lang in ['en_US', 'zh_CN']:
                file_path = os.path.join(self.i18n_dir, f'{lang}.json')
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.translations[lang] = json.load(f)
                else:
                    logger.warning(f"Language file not found: {file_path}")
        except Exception as e:
            logger.error(f"Failed to load translations: {str(e)}")
    
    def set_language(self, lang):
        """设置当前语言"""
        if lang in self.translations:
            self.current_lang = lang
            return True
        return False
    
    def get_text(self, key, default=''):
        """获取翻译文本"""
        try:
            # 支持使用点号访问嵌套键
            keys = key.split('.')
            value = self.translations.get(self.current_lang, {})
            for k in keys:
                value = value.get(k, default)
            return value if value != default else key
        except Exception:
            return key
    
    def get_available_languages(self):
        """获取可用的语言列表"""
        return list(self.translations.keys())
    
    def format_text(self, key, **kwargs):
        """获取带格式化参数的翻译文本"""
        text = self.get_text(key)
        try:
            return text.format(**kwargs)
        except Exception:
            return text 